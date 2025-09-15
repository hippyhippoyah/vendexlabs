import os
import json
from datetime import datetime, timedelta, timezone
import logging

import requests
import feedparser
import dateutil.parser
from bs4 import BeautifulSoup
from cleanco import basename
import peewee

from sender import send_email_ses
from models import db, RSSFeed, Vendor, VendorList, VendorListVendor, Subscriber, VendorListSubscriber

API_URL = "https://api.openai.com/v1/chat/completions"
API_KEY = os.getenv("API_KEY")
RSS_FEED_URLS = os.getenv("RSS_FEED_URLS", "[]")
FEEDS = json.loads(RSS_FEED_URLS)

logging.basicConfig(level=logging.INFO)
logging.getLogger().setLevel(logging.INFO)

def call_openai_api(messages, max_tokens=1000, temperature=0):
    headers = {"Authorization": f"Bearer {API_KEY}"}
    data = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    try:
        response = requests.post(API_URL, headers=headers, json=data)
        response.raise_for_status()
        response_json = response.json()
        return response_json["choices"][0]["message"]["content"]
    except Exception as e:
        logging.error(f"OpenAI API call failed: {e}")
        return None

def is_dupe(results, entry):
    prompt = f"""Article: {entry[0]}.
    Is the given article a duplicate of the following articles?
    {results}.
    Answer with only "YES" or "NO".
    """
    messages = [{"role": "user", "content": prompt}]
    response_text = call_openai_api(messages)
    if response_text and "YES" in response_text.upper():
        logging.info(f"Duplicate found: {entry[0]}")
        return True
    return False

def query_AI_extraction(summary):
    prompt = f"""Article: {summary}. 
    If the article is not about a security incident, return nothing.
    If it is, answer the following:
    Based on the Article, What compromised entity is mentioned in the summary?
    What product is affected in the summary?
    How much has this product been exploited?
    Summary of the article in 100 words.
    Incident Type: Potential unauthorized access or data exfiltration.
    Affected Service: [Service Name].
    Potentially Impacted Data: [Specify the type of data, e.g., customer information, login credentials, etc.]
    Status: The incident is under active investigation, with immediate steps underway to mitigate potential impact.
    """
    system_prompt = (
        'You are a JSON only responder. If the article is not about a security incident, return nothing (empty response). '
        'Otherwise, respond with a format like this, if not certain about a field give None: '
        '{"vendor": "vendorName", "product": "productName", "exploits": "", "summary":"summary", '
        '"incident_type": "", '
        '"affected_service": "", '
        '"potentially_impacted_data": "[Specify the type of data, e.g., customer information, login credentials, etc.]", '
        '"status": "Status of Event"} '
        'Do not say anything else in the response. Do not include explanations, apologies, or any text outside of the JSON block. '
        'If unsure, still answer in the same format but with null objects.'
    )
    messages = [
        {"role": "user", "content": prompt},
        {"role": "system", "content": system_prompt}
    ]
    response_text = call_openai_api(messages, max_tokens=500)
    if not response_text or not response_text.strip():
        return None
    try:
        return json.loads(response_text)
    except Exception as e:
        logging.error(f"Error parsing API response: {e} + {response_text}")
        return None

def fetch_article_text(url):
    try:
        logging.info(f"Fetching article text from: {url}")
        response = requests.get(url, timeout=10, headers={"User-Agent": "Chrome/58.0.3029.110 Safari/537.3"})
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        content = soup.find_all('p')
        return " ".join([p.get_text() for p in content])
    except Exception as e:
        logging.warning(f"Failed to fetch article: {url}, error: {e}")
        return ""

def create_entries(feeds, last_published):
    new_entries = []
    for feed_info in feeds:
        source = feed_info.get("source", "Unknown")
        url = feed_info.get("url")
        if not url:
            continue
        feed = feedparser.parse(url)
        for entry in feed.entries:
            article_text = fetch_article_text(entry.link)
            if not article_text:
                logging.info(f"Skipping article with no text: {entry.link}")
                continue
            entry_published = dateutil.parser.parse(entry.published) if hasattr(entry, 'published') else None
            if not entry_published or entry_published <= last_published:
                break
            res = query_AI_extraction(article_text)
            if not res:
                continue
            logging.info(res)
            vendor = res.get('vendor')
            if not vendor:
                logging.info("Skipping entry with unknown vendor")
                continue
            vendor = basename(vendor).upper()
            product = res.get('product', 'Unknown')
            exploits = res.get('exploits', 'None')
            summary = res.get('summary', 'None')
            img = entry.enclosures[0]['url'] if entry.enclosures else None
            incident_type = res.get('incident_type', "Potential unauthorized access or data exfiltration.")
            affected_service = res.get('affected_service', "[Service Name]")
            potentially_impacted_data = res.get('potentially_impacted_data', "[Specify the type of data, e.g., customer information, login credentials, etc.]")
            status = res.get('status', "The incident is under active investigation, with immediate steps underway to mitigate potential impact.")
            new_entries.append((
                entry.title, vendor, product, entry_published, exploits, summary, entry.link, img,
                incident_type, affected_service, potentially_impacted_data, status, source
            ))
    return new_entries

def dedupe_entries(new_entries, window_days=60):
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

def insert_entries(entries):
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
                img=entry[7],
                incident_type=entry[8],
                affected_service=entry[9],
                potentially_impacted_data=entry[10],
                status=entry[11],
                source=entry[12]
            )
        except peewee.IntegrityError:
            continue

    emails_count = 0
    for entry in entries:
        vendor_name = entry[1] or "Unknown"
        try:
            vendor_obj = Vendor.get_or_none(Vendor.name == vendor_name)
        except Exception as e:
            logging.warning(f"Vendor lookup failed for {vendor_name}: {e}")
            vendor_obj = None
        emails = set()
        if vendor_obj:
            vendor_list_ids = VendorListVendor.select(VendorListVendor.vendor_list).where(VendorListVendor.vendor == vendor_obj)
            subscriber_query = Subscriber.select(Subscriber.email).join(VendorListSubscriber, on=(Subscriber.id == VendorListSubscriber.subscriber)).where(VendorListSubscriber.vendor_list.in_(vendor_list_ids), Subscriber.verified == True)
            emails.update([subscriber.email for subscriber in subscriber_query if subscriber.email])
        emails.add("vendexlabs+notification@gmail.com")
        # Deduplicate emails before sending
        unique_emails = set(emails)
        if unique_emails:
            emails_count += len(unique_emails)
            logging.info(f"Sending email to: {list(unique_emails)}")
            for email in unique_emails:
                send_email_ses([email], entry)
    return emails_count

def lambda_handler(event, context):
    try:
        current_time = datetime.now(timezone.utc)
        hours_ago = event.get("hours", 3)
        last_published = current_time - timedelta(hours=hours_ago)
        db.connect(reuse_if_open=True)
        new_entries = create_entries(FEEDS, last_published)
        logging.info(f"Since last published: {last_published}")
        if not new_entries:
            return {"statusCode": 200, "body": "No new entries found."}
        new_entries = dedupe_entries(new_entries)
        logging.info("Inserting entries...")
        emails_count = insert_entries(new_entries)
        db.close()
        return {"statusCode": 200, "body": f"Inserted {len(new_entries)} new entries. Sent {emails_count} emails."}
    except Exception as e:
        logging.error(f"Error in lambda_handler: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
