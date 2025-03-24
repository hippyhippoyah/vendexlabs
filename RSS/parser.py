import os
import psycopg2
import feedparser
import json
import boto3
import requests
from datetime import datetime

# AWS SSM Client
ssm = boto3.client('ssm')

# Read environment variables
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")

RSS_FEED_URL = os.getenv("RSS_FEED_URL")
PARAMETER_NAME = "/rss/last_published"
API_URL = "https://router.huggingface.co/fireworks-ai/inference/v1/chat/completions"
API_KEY = os.getenv("HUGGINGFACE_API_KEY")

def get_last_published():
    """Retrieve last inserted date from AWS Parameter Store"""
    try:
        response = ssm.get_parameter(Name=PARAMETER_NAME)
        return response['Parameter']['Value']
    except ssm.exceptions.ParameterNotFound:
        return "2000-01-01T00:00:00Z"  

def update_last_published(new_date):
    """Update the last inserted date in AWS Parameter Store"""
    ssm.put_parameter(
        Name=PARAMETER_NAME,
        Value=new_date,
        Type="String",
        Overwrite=True
    )

def query_vendor_extraction(summary, info="vendor"):
    """Query the API to extract {info} information"""
    headers = {"Authorization": f"Bearer {API_KEY}"}
    prompt = f"""Context: {summary}. 
    Based on the Context, What {info} is affected?
    Answer with one word being the {info} affected. 
    Do not say anything else in the response."""
    
    response = requests.post(API_URL, headers=headers, json={
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 500,
        "model": "accounts/fireworks/models/llama-v3-8b-instruct"
    })
    
    return response.json()["choices"][0]["message"]["content"]

def lambda_handler(event, context):
    try:
        last_published = get_last_published()

        feed = feedparser.parse(RSS_FEED_URL)
        new_entries = []

        for entry in feed.entries:
            entry_published = entry.published if hasattr(entry, 'published') else None
            if entry_published and entry_published > last_published:
                vendor = query_vendor_extraction(entry.summary)
                product = entry.get('product', 'Unknown')
                exploits = entry.get('exploits', 'None')
                new_entries.append((entry.title, vendor, product, entry_published, exploits, entry.summary, entry.link))

        # Insert only new entries
        if new_entries:
            conn = psycopg2.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASS,
                dbname=DB_NAME
            )
            cursor = conn.cursor()
            cursor.executemany(
                """
                INSERT INTO rss_feeds (title, vendor, product, published, exploits, summary, url)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (title) DO NOTHING;
                """,
                new_entries
            )
            conn.commit()
            cursor.close()
            conn.close()

            # Update Parameter Store with the newest entry date
            update_last_published(max(entry[3] for entry in new_entries))

        return {"statusCode": 200, "body": f"Inserted {len(new_entries)} new entries."}

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
    
lambda_handler(None, None)