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
from bs4 import BeautifulSoup
from cleanco import basename

# Read environment variables
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")

RSS_FEED_URLS = os.getenv("RSS_FEED_URLS", "[]")
PARAMETER_NAME = "/rss/last_published"
API_URL = "https://api.openai.com/v1/chat/completions"
API_KEY = os.getenv("API_KEY")
FEEDS = json.loads(RSS_FEED_URLS)

def is_dupe(results, entry):
    # Temp matching, TODO is to prompt chatbot for better matching
    headers = {"Authorization": f"Bearer {API_KEY}"}
    prompt = f"""Article: {entry[0]}.
    Is the given article a duplicate of the following articles?
    {results}.
    Answer with only "YES" or "NO".
    """
    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 300
    }

    try:
        response = requests.post(API_URL, headers=headers, json=data)
        response.raise_for_status()  # Raise an exception for HTTP errors
        response_content = response.content.decode('utf-8')
        response_json = json.loads(response_content)
        response_text = response_json["choices"][0]["message"]["content"]
        if "YES" in response_text.upper():
            print("Duplicate found: " + entry[0])
            return True
    except requests.exceptions.RequestException as e:
        print(f"HTTP Dedupe Request failed: {e}")
        return False
    return True

def query_AI_extraction(summary):
    headers = {"Authorization": f"Bearer {API_KEY}"}
    prompt = f"""Article: {summary}. 
    Based on the Article, What compromised entity is mentioned in the summary?
    What product is affected in the summary?
    How much has this product been exploited?
    Summary of the article in 100 words. 
    Answer with only json format like this: {{"vendor": "vendorName", "product": "productName", "exploits": "", "summary":"summary"}}.
    Do not say anything else in the response. If unsure, still answer in the same format but with null objects."""
    
    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 300
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=data)
        response.raise_for_status()  # Raise an exception for HTTP errors
        response_content = response.content.decode('utf-8')
        response_json = json.loads(response_content)
        return json.loads(response_json["choices"][0]["message"]["content"])
    except requests.exceptions.RequestException as e:
        print(f"HTTP Request failed: {e}")
        return {"vendor": None, "product": None, "exploits": None, "summary": None}
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error parsing API response: {e} + {response_content}")
        return {"vendor": None, "product": None, "exploits": None, "summary": None}

def create_entries(feed, last_published):
    new_entries = []
    for url in FEEDS:
        print("Parsing: " + url)
        feed = feedparser.parse(url)   

        for entry in feed.entries:
            response = requests.get(entry.link, timeout=10, headers={"User-Agent": "Chrome/58.0.3029.110 Safari/537.3"})
            if response.status_code != 200:
                print(f"Failed to fetch article: {entry.link}, status code: {response.status_code}")
                continue
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            content = soup.find_all('p')
            article_text = " ".join([p.get_text() for p in content])
            entry_published = dateutil.parser.parse(entry.published) if hasattr(entry, 'published') else None
            if entry_published and entry_published > last_published:
                res = query_AI_extraction(article_text)
                print(res)
                vendor = res.get('vendor', None)
                if vendor is not None:
                    vendor = basename(vendor).upper()
                else:
                    print("Skipping entry with unknown vendor")
                    continue
                product = res.get('product', 'Unknown')
                exploits = res.get('exploits', 'None')
                summary = res.get('summary', 'None')
                img = entry.enclosures[0]['url'] if entry.enclosures else None
                new_entries.append((entry.title, vendor, product, entry_published, exploits, summary, entry.link, img))
            else:
                continue
    return new_entries


def lambda_handler(event, context):
    try:
        current_time = datetime.now(timezone.utc).replace(tzinfo=timezone.utc)
        hours_ago = event.get("hours", 3)
        last_published = current_time - timedelta(hours=hours_ago)
        new_entries = create_entries(FEEDS, last_published)
        print("Since last published: " + str(last_published))
        # Insert only new entries
        if not new_entries:
            return {"statusCode": 200, "body": f"No new entries found."}
        conn = psycopg2.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            dbname=DB_NAME,
            connect_timeout=10 
        )
        cursor = conn.cursor()
        # Dedupe
        print("Deduping entries...")
        one_month_ago = datetime.now(timezone.utc) - timedelta(days=30)
        filtered_entries = []
        for entry in new_entries:
            vendor = entry[1] or "Unknown"
            cursor.execute(
                """
                SELECT title, summary FROM rss_feeds 
                WHERE published > %s AND vendor = %s
                """,
                (one_month_ago, vendor)
            )
            results = cursor.fetchall()
            if not results:  # If no matches, keep the entry
                filtered_entries.append(entry)
            elif not is_dupe(results, entry):
                filtered_entries.append(entry)

        new_entries = filtered_entries

        print("Inserting entries...")
        cursor.executemany(
            """
            INSERT INTO rss_feeds (title, vendor, product, published, exploits, summary, url, img)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (url) DO NOTHING;
            """,
            new_entries
        )
        emails_count = 0
        for entry in new_entries:
            print(entry)
            vendor = entry[1] or "Unknown"
            cursor.execute("SELECT emails FROM vendors WHERE vendor = %s", (vendor,))
            results = cursor.fetchall()
            if results:
                emails_count += len(results)
                emails = [row[0] for row in results]
                print(f"Sending email to: {emails}")
                send_email_ses(emails, entry)
                time.sleep(1) # I honestly don't know if this is needed


        conn.commit()
        cursor.close()
        conn.close()

        return {"statusCode": 200, "body": f"Inserted {len(new_entries)} new entries. Sent {emails_count} emails."}

    except Exception as e:
        print(f"Error in lambda_handler: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
    