import json
from datetime import datetime
import requests
from cleanco import basename
from peewee import IntegrityError
from config import db
from models import VendorInfo

API_URL = "https://api.openai.com/v1/chat/completions"
import os
API_KEY = os.getenv("API_KEY")

def generate_vendor_info(vendor_name):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    prompt = f"""Provide the following information about the company '{vendor_name}':
- vendor: {vendor_name}
- s_and_c_cert: List of security and compliance certifications (as a JSON array)
- bus_type: What kind of business (choose one or more: 'B2B as a SaaS', 'B2C', or 'B2B as a service provider') (as a JSON array)
- data_collected: What kind of data does it collect from customers?
- legal_compliance: Does the data have any legal/compliance implications?
- published_subprocessors: List the published subprocessor list (as a JSON array)
- privacy_policy_url: The URL for the privacy policy. This must be a real, working URL from the official vendor website. Do not guess or fabricate. Visit the vendor's official website and copy the actual link.
- terms_of_service_url: The URL for the terms of service or terms of condition policy. This must be a real, working URL from the official vendor website. Do not guess or fabricate. Visit the vendor's official website and copy the actual link.
- date: Today's date in YYYY-MM-DD format

You must search the official vendor website and reputable sources to find this information. Only provide real, verified URLs. Do not make up or guess URLs. Respond in valid JSON format with these fields only. Do not include any extra text or explanation."""
    system_prompt = f"""You must respond in JSON format only. Do not include any other text or explanations.
Your response must use only real, verified information from the official vendor website or reputable sources. For URLs, you must visit the official vendor website and copy the actual, working links. Do not guess, fabricate, or use placeholders for URLs. If a URL does not exist, use an empty string.

Your response should look like this, but with the relevant and correct information about the vendor:
Example: {{
"vendor": "vendorName",
"s_and_c_cert": ["SOC2", "ISO27001"],
"bus_type": ["B2B","B2C"],
"data_collected": "Customer names, emails, usage data",
"legal_compliance": "GDPR, CCPA",
"published_subprocessors": ["AWS", "Stripe"],
"privacy_policy_url": "https://vendor.com/privacy-policy",
"terms_of_service_url": "https://vendor.com/terms",
"date": "YYYY-MM-DD"
}}"""
    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 512,
        "temperature": 0
    }
    response = requests.post(API_URL, headers=headers, json=data)
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    try:
        # Strip leading text before JSON object
        json_start = content.find('{')
        if json_start != -1:
            content = content[json_start:]
        return json.loads(content)
    except Exception as e:
        print(f"Failed to parse JSON from model: {e}\nRaw content: {content}")
        return None

def add_info_to_db(vendors):
    if not vendors:
        print("No vendors to add.")
        return {
            'statusCode': 400,
            'body': json.dumps('No vendors to add.')
        }
    db.connect(reuse_if_open=True)
    updated_vendors = []
    inserted_vendors = []
    for vendor in vendors:
        if isinstance(vendor, dict):
            vendor_name = vendor.get('vendor') or vendor.get('vendor_name')
        else:
            vendor_name = vendor
        if not vendor_name:
            continue

        normalized_vendor = basename(vendor_name).upper()
        vendor_info = generate_vendor_info(normalized_vendor)
        if not vendor_info:
            print(f"Could not generate info for {normalized_vendor}")
            continue

        try:
            obj, created = VendorInfo.get_or_create(
                vendor=normalized_vendor,
                defaults={
                    "s_and_c_cert": json.dumps(vendor_info.get('s_and_c_cert', [])),
                    "bus_type": json.dumps(vendor_info.get('bus_type', [])),
                    "data_collected": vendor_info.get('data_collected'),
                    "legal_compliance": vendor_info.get('legal_compliance'),
                    "published_subprocessors": json.dumps(vendor_info.get('published_subprocessors', [])),
                    "privacy_policy_url": vendor_info.get('privacy_policy_url'),
                    "tos_url": vendor_info.get('terms_of_service_url'),
                    "date": vendor_info.get('date')
                }
            )
            if not created:
                # Update existing
                obj.s_and_c_cert = json.dumps(vendor_info.get('s_and_c_cert', []))
                obj.bus_type = json.dumps(vendor_info.get('bus_type', []))
                obj.data_collected = vendor_info.get('data_collected')
                obj.legal_compliance = vendor_info.get('legal_compliance')
                obj.published_subprocessors = json.dumps(vendor_info.get('published_subprocessors', []))
                obj.privacy_policy_url = vendor_info.get('privacy_policy_url')
                obj.tos_url = vendor_info.get('terms_of_service_url')
                obj.date = vendor_info.get('date')
                obj.save()
                updated_vendors.append(normalized_vendor)
            else:
                inserted_vendors.append(normalized_vendor)
                print(f"Inserted {normalized_vendor} into the database.")
        except Exception as e:
            print(f"Error adding vendor info to database: {e}")
            db.rollback()
            continue
    db.close()
    return {
        'statusCode': 200,
        'body': json.dumps({
            'Updated': updated_vendors,
            'Inserted': inserted_vendors
        })
    }

def get_vendor_info_from_db(vendor_names):
    db.connect(reuse_if_open=True)
    results = []
    for vendor in vendor_names:
        normalized_vendor = basename(vendor).upper()
        try:
            obj = VendorInfo.select().where(VendorInfo.vendor ** f"%{normalized_vendor}%").first()
            if obj:
                vendor_info = {
                    "vendor": obj.vendor,
                    "s_and_c_cert": json.loads(obj.s_and_c_cert) if obj.s_and_c_cert else [],
                    "bus_type": json.loads(obj.bus_type) if obj.bus_type else [],
                    "data_collected": obj.data_collected,
                    "legal_compliance": obj.legal_compliance,
                    "published_subprocessors": json.loads(obj.published_subprocessors) if obj.published_subprocessors else [],
                    "privacy_policy_url": obj.privacy_policy_url,
                    "tos_url": obj.tos_url,
                    "date": obj.date
                }
                results.append(vendor_info)
            else:
                print(f"No info found for {normalized_vendor}")
        except Exception as e:
            print(f"Error querying database: {e}")
            continue
    db.close()
    print(f"Results: {results}")
    return {
        'statusCode': 200,
        'body': json.dumps(results, default=str)
    }

def lambda_handler(event, context):
    try:
        method = event['requestContext']['http']['method']
        method = method.upper()
    except KeyError:
        return {
            'statusCode': 400,
            'body': json.dumps('Bad Request: No HTTP method found')
        }
    if method == 'POST':
        body = event.get('body')
        if body:
            data = json.loads(body) if isinstance(body, str) else body
        else:
            data = event
        vendors = data.get('vendors', [])
        return add_info_to_db(vendors)
    elif method == 'GET':
        vendor_names = event.get('queryStringParameters', {}).get('vendors', [])
        print(f"Vendor names: {vendor_names}")
        if isinstance(vendor_names, str):
            vendor_names = [v.strip() for v in vendor_names.split(',')]
        return get_vendor_info_from_db(vendor_names)


