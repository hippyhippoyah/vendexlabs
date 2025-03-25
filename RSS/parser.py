import os
import psycopg2
import feedparser
import json
import boto3
import requests
from datetime import datetime, timedelta

# Read environment variables
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")

RSS_FEED_URL = os.getenv("RSS_FEED_URL")
PARAMETER_NAME = "/rss/last_published"
API_URL = "https://router.huggingface.co/fireworks-ai/inference/v1/chat/completions"
API_KEY = os.getenv("API_KEY")

# Remove SSM client initialization
# ssm = None

# Remove get_ssm_client function
# def get_ssm_client():
#     global ssm
#     if ssm is None:
#         ssm = boto3.client('ssm', config=boto3.session.Config(connect_timeout=5, read_timeout=5))
#     return ssm

# Remove get_last_published function
# def get_last_published():
#     """Retrieve last inserted date from AWS Parameter Store"""
#     try:
#         print("Getting SSM client...")
#         ssm_client = get_ssm_client()
#         print("Fetching parameter from SSM...")
#         response = ssm_client.get_parameter(Name=PARAMETER_NAME)
#         print("Parameter fetched successfully.")
#         return response['Parameter']['Value']
#     except ssm_client.exceptions.ParameterNotFound:
#         print("Parameter not found, returning default date.")
#         return "2000-01-01T00:00:00Z"
#     except Exception as e:
#         print(f"Error fetching parameter: {e}")
#         raise

# Remove update_last_published function
# def update_last_published(new_date):
#     """Update the last inserted date in AWS Parameter Store"""
#     ssm_client = get_ssm_client()
#     ssm_client.put_parameter(
#         Name=PARAMETER_NAME,
#         Value=new_date,
#         Type="String",
#         Overwrite=True
#     )

def query_vendor_extraction(summary, info="vendor"):
    """Query the API to extract {info} information"""
    headers = {"Authorization": f"Bearer {API_KEY}"}
    prompt = f"""Context: {summary}. 
    Based on the Context, What {info} is affected?
    Answer with one word being the {info} affected. 
    Do not say anything else in the response."""
    
    # response = requests.post(API_URL, headers=headers, json={
    #     "messages": [
    #         {
    #             "role": "user",
    #             "content": prompt
    #         }
    #     ],
    #     "max_tokens": 500,
    #     "model": "accounts/fireworks/models/llama-v3-8b-instruct"
    # })
    return("VENDOR (IM BROKE)")
    # return response.json()["choices"][0]["message"]["content"]

def lambda_handler(event, context):
    print("Starting RSS feed parser...")
    try:
        # Get the current time and the time 3 hours ago
        current_time = datetime.utcnow()
        last_published = (current_time - timedelta(hours=3)).isoformat() + "Z"
        print(f"Fetching articles published after: {last_published}")

        feed = feedparser.parse(RSS_FEED_URL)
        new_entries = []
        print("Parsing feed entries...")

        for entry in feed.entries:
            entry_published = entry.published if hasattr(entry, 'published') else None
            if entry_published and entry_published > last_published:
                vendor = query_vendor_extraction(entry.summary)
                product = entry.get('product', 'Unknown')
                exploits = entry.get('exploits', 'None')
                new_entries.append((entry.title, vendor, product, entry_published, exploits, entry.summary, entry.link))

        # Insert only new entries
        print("Inserting new entries...")
        if new_entries:
            conn = psycopg2.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASS,
                dbname=DB_NAME,
                connect_timeout=10 
            )
            cursor = conn.cursor()
            cursor.executemany(
                """
                INSERT INTO rss_feeds (title, vendor, product, published, exploits, summary, url)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (url) DO NOTHING;
                """,
                new_entries
            )
            conn.commit()
            cursor.close()
            conn.close()

        return {"statusCode": 200, "body": f"Inserted {len(new_entries)} new entries."}

    except Exception as e:
        print(f"Error in lambda_handler: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
    
lambda_handler(None, None)