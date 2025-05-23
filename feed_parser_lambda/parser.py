# --- Standard library imports ---
import os
import json
from datetime import datetime, timedelta, timezone

# --- Third-party imports ---
import requests
import feedparser
import dateutil.parser
from bs4 import BeautifulSoup
from cleanco import basename
import peewee

# --- Local imports ---
from sender import send_email_ses
from models import db, RSSFeed, Subscription

# --- Configuration ---
API_URL = "https://api.openai.com/v1/chat/completions"
API_KEY = os.getenv("API_KEY")
RSS_FEED_URLS = os.getenv("RSS_FEED_URLS", "[]")
FEEDS = json.loads(RSS_FEED_URLS)

def is_dupe(results, entry) -> bool:
    """Check if entry is a duplicate using OpenAI API."""
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

def query_AI_extraction(summary: str) -> dict:
    """Extract vendor, product, exploits, and summary from article using OpenAI API."""
    headers = {"Authorization": f"Bearer {API_KEY}"}
    prompt = f"""Article: {summary}. 
    Based on the Article, What compromised entity is mentioned in the summary?
    What product is affected in the summary?
    How much has this product been exploited?
    Summary of the article in 100 words. 
    """
    system_prompt = f"""You are a JSON only responder. Respond with a format like this: {{"vendor": "vendorName", "product": "productName", "exploits": "", "summary":"summary"}}
    Do not say anything else in the response. Do not include explanations, apologies, or any text outside of the JSON block. If unsure, still answer in the same format but with null objects."""
    
    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "user", "content": prompt},
            {"role": "system", "content": system_prompt}
        ],
        "temperature":0,
        "max_tokens": 500
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

def fetch_article_text(url: str) -> str:
    """Fetch and return the article text from a URL."""
    response = requests.get(url, timeout=10, headers={"User-Agent": "Chrome/58.0.3029.110 Safari/537.3"})
    if response.status_code != 200:
        print(f"Failed to fetch article: {url}, status code: {response.status_code}")
        return ""
    soup = BeautifulSoup(response.content, 'html.parser')
    content = soup.find_all('p')
    return " ".join([p.get_text() for p in content])

def create_entries(feeds: list, last_published: datetime) -> list:
    """Parse feeds and return new entries since last_published."""
    new_entries = []
    for url in feeds:
        print("Parsing: " + url)
        feed = feedparser.parse(url)
        for entry in feed.entries:
            article_text = fetch_article_text(entry.link)
            if not article_text:
                continue
            entry_published = dateutil.parser.parse(entry.published) if hasattr(entry, 'published') else None
            if entry_published and entry_published > last_published:
                res = query_AI_extraction(article_text)
                print(res)
                vendor = res.get('vendor')
                if vendor:
                    vendor = basename(vendor).upper()
                else:
                    print("Skipping entry with unknown vendor")
                    continue
                product = res.get('product', 'Unknown')
                exploits = res.get('exploits', 'None')
                summary = res.get('summary', 'None')
                img = entry.enclosures[0]['url'] if entry.enclosures else None
                new_entries.append((entry.title, vendor, product, entry_published, exploits, summary, entry.link, img))
    return new_entries

def dedupe_entries(new_entries: list, window_days: int = 60) -> list:
    """Remove duplicate entries using AI deduplication."""
    one_month_ago = datetime.now(timezone.utc) - timedelta(days=window_days)
    filtered_entries = []
    for entry in new_entries:
        vendor = entry[1] or "Unknown"
        results = list(
            RSSFeed.select(RSSFeed.title, RSSFeed.summary)
            .where(
                (RSSFeed.published > one_month_ago) &
                (RSSFeed.vendor == vendor)
            )
            .tuples()
        )
        if not results or not is_dupe(results, entry):
            filtered_entries.append(entry)
    return filtered_entries

def insert_entries(entries: list):
    """Insert entries into the database, skipping duplicates."""
    for entry in entries:
        try:
            RSSFeed.create(
                title=entry[0],
                vendor=entry[1],
                product=entry[2],
                published=entry[3],
                exploits=entry[4],
                summary=entry[5],
                url=entry[6],
                img=entry[7]
            )
        except peewee.IntegrityError:
            continue

def send_notifications(entries: list) -> int:
    """Send email notifications for new entries."""
    emails_count = 0
    for entry in entries:
        vendor = entry[1] or "Unknown"
        send_email_ses(["vendexlabs+notification@gmail.com"], entry)
        results = Subscription.select(Subscription.emails).where(Subscription.vendor == vendor)
        emails = [row.emails for row in results]
        if emails:
            emails_count += len(emails)
            print(f"Sending email to: {emails}")
            for email in emails:
                send_email_ses([email], entry)
    return emails_count

def lambda_handler(event, context):
    """AWS Lambda entrypoint."""
    try:
        current_time = datetime.now(timezone.utc)
        hours_ago = event.get("hours", 3)
        last_published = current_time - timedelta(hours=hours_ago)
        db.connect(reuse_if_open=True)
        new_entries = create_entries(FEEDS, last_published)
        print("Since last published: " + str(last_published))
        if not new_entries:
            return {"statusCode": 200, "body": f"No new entries found."}
        new_entries = dedupe_entries(new_entries)
        print("Inserting entries...")
        insert_entries(new_entries)
        emails_count = send_notifications(new_entries)
        db.close()
        return {"statusCode": 200, "body": f"Inserted {len(new_entries)} new entries. Sent {emails_count} emails."}
    except Exception as e:
        print(f"Error in lambda_handler: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
