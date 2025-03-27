import os
import psycopg2
import feedparser
import json
import boto3
import requests
from datetime import datetime, timedelta, timezone
import dateutil.parser
from sender import send_email_ses
import time

# Read environment variables
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")

RSS_FEED_URL = os.getenv("RSS_FEED_URL")
PARAMETER_NAME = "/rss/last_published"
API_URL = "https://api.openai.com/v1/chat/completions"
API_KEY = os.getenv("API_KEY")

def query_vendor_extraction(summary, info="vendor"):
    headers = {"Authorization": f"Bearer {API_KEY}"}
    prompt = f"""Context: {summary}. 
    Based on the Context, What {info} is affected?
    Answer with one word being the {info} affected. 
    Do not say anything else in the response."""
    
    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 100
    }
    
    response = requests.post(API_URL, headers=headers, json=data)
    response_json = response.json()
    print(response_json["choices"][0]["message"]["content"])
    return response_json["choices"][0]["message"]["content"]

def lambda_handler(event, context):
    print("Starting RSS feed parser...")
    try:
        # Get the current time and the time x hours ago
        current_time = datetime.utcnow().replace(tzinfo=timezone.utc)
        hours_ago = event.get("hours", 3)
        last_published = current_time - timedelta(hours=hours_ago)


        feed = feedparser.parse(RSS_FEED_URL)
        new_entries = []
        print("Parsing feed entries...")
        print("first is: ", feed.entries[0])    

        for entry in feed.entries:
            entry_published = dateutil.parser.parse(entry.published) if hasattr(entry, 'published') else None
            if entry_published and entry_published > last_published:
                vendor = query_vendor_extraction(entry.summary)
                product = entry.get('product', 'Unknown')
                exploits = entry.get('exploits', 'None')
                new_entries.append((entry.title, vendor, product, entry_published, exploits, entry.summary, entry.link))

        emails_count = 0
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
            for entry in new_entries:
                title, vendor, product, published, exploits, summary, url = entry
                cursor.execute("SELECT emails FROM vendors WHERE vendor = %s", (vendor,))
                results = cursor.fetchall()
                if results:
                    emails_count += len(results)
                    emails = [row[0] for row in results]
                    print(f"Sending email to: {emails}")
                    subject = f"New RSS Feed Entry for {vendor}"
                    body = f"Title: {title}\nVendor: {vendor}\nProduct: {product}\nPublished: {published}\nExploits: {exploits}\nSummary: {summary}\nURL: {url}"
                    send_email_ses(emails, subject, body)
                    time.sleep(1)


            conn.commit()
            cursor.close()
            conn.close()

        return {"statusCode": 200, "body": f"Inserted {len(new_entries)} new entries. Sent {emails_count} emails."}

    except Exception as e:
        print(f"Error in lambda_handler: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
    