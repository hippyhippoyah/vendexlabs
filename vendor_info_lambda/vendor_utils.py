import json
import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from models import VendorInfo


GOOGLE_SEARCH_URL = os.getenv("GOOGLE_SEARCH_URL", "https://www.googleapis.com/customsearch/v1")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

API_KEY = os.getenv("API_KEY")
API_URL = os.getenv("OPENAI_API_URL", "https://api.openai.com/v1/chat/completions")


def google_custom_search(query, search_type=None, **kwargs):
    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        raise ValueError("Google API key or CSE ID not set in environment variables.")
    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CSE_ID,
        "q": query,
    }
    if search_type:
        params["searchType"] = search_type
    params.update(kwargs)
    response = requests.get(GOOGLE_SEARCH_URL, params=params)
    response.raise_for_status()
    results = response.json()
    if "items" in results and len(results["items"]) > 0:
        return results["items"][0].get("link", "")
    return ""

def google_custom_image_search(query, **kwargs):
    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        raise ValueError("Google API key or CSE ID not set in environment variables.")
    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CSE_ID,
        "q": query,
        "searchType": "image",
        "num": 1
    }
    params.update(kwargs)
    response = requests.get(GOOGLE_SEARCH_URL, params=params)
    response.raise_for_status()
    results = response.json()
    if "items" in results and len(results["items"]) > 0:
        return results["items"][0].get("link", "")
    return ""

def search_official_website(vendor_name):
    # Use Google Custom Search to find the official website
    query = f"{vendor_name} official website"
    return google_custom_search(query)

def llm_json_response(prompt):
    """
    Send a prompt to the LLM and return the parsed JSON response.
    """
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    system_prompt = (
        "You must respond in JSON format only. Do not include any other text or explanations."
        " Your response must use only real, verified information from official or reputable sources."
        " If a value does not exist, use an empty string or empty array as appropriate."
    )
    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    }
    response = requests.post(API_URL, headers=headers, json=data)

    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    try:
        # Use regex to extract the first JSON object or array from the response
        match = re.search(r'(\{.*\}|\[.*\])', content, re.DOTALL)
        if match:
            json_str = match.group(1)
            return json.loads(json_str)
        else:
            # Fallback to previous logic
            json_start = content.find('{')
            if json_start != -1:
                content = content[json_start:]
            return json.loads(content)
    except Exception as e:
        print(f"Failed to parse JSON from model: {e}\nRaw content: {content}")
        return None

def get_vendor_logo(vendor_name, website_url=None):
    query = f"{vendor_name} logo"
    logo_url = google_custom_search(query, search_type="image")
    if not logo_url and website_url:
        logo_url = google_custom_search(f"{website_url} logo", search_type="image")
    return logo_url

def scrape_website_for_fields(website_url, vendor_name=None):
    """
    Use Google Search API to find relevant URLs (privacy policy, tos, contact, etc.)
    and LLM to extract structured info from the website context.
    """
    # Use Google Search to find privacy policy and tos URLs
    privacy_policy_url = google_custom_search(f"{website_url} privacy policy") or f"{website_url}/privacy"
    tos_url = google_custom_search(f"{website_url} terms of service") or f"{website_url}/tos"
    contact_url = google_custom_search(f"{website_url} contact") or f"{website_url}/contact"

    logo_url = get_vendor_logo(vendor_name or website_url, website_url)

    # Compose LLM prompt
    prompt = (
        f"Given the official website {website_url}, privacy policy URL {privacy_policy_url}, "
        f"terms of service URL {tos_url}, and contact page {contact_url}, "
        "extract the following fields as JSON:\n"
        "{"
        "\"logo\": (URL to the company's logo), "
        "\"contact_email\": (official contact email), "
        "\"headquarters_location\": (company headquarters location), "
        "\"privacy_policy_url\": (privacy policy URL), "
        "\"tos_url\": (terms of service URL)"
        "}\n"
        "Use only real, verifiable information. If a value does not exist, use an empty string."
    )
    llm_result = llm_json_response(prompt)
    if not llm_result:
        llm_result = {
            "logo": logo_url,
            "contact_email": f"info@{website_url.split('//')[1]}",
            "headquarters_location": "",
            "privacy_policy_url": privacy_policy_url,
            "tos_url": tos_url
        }
    else:
        llm_result["logo"] = logo_url or llm_result.get("logo", "")
    return llm_result

def extract_fields_with_llm(privacy_policy_url, tos_url, website_url):
    """
    Fetch and parse privacy policy and ToS pages, then use LLM to extract fields.
    """
    def fetch_text(url):
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            texts = soup.stripped_strings
            return " ".join(texts)[:4000]  # Limit to 4000 chars for prompt size
        except Exception as e:
            print(f"Failed to fetch or parse {url}: {e}")
            return ""

    privacy_text = fetch_text(privacy_policy_url) if privacy_policy_url else ""
    tos_text = fetch_text(tos_url) if tos_url else ""

    prompt = (
        f"Given the following information from the vendor's website ({website_url}):\n"
        f"Privacy Policy:\n{privacy_text}\n\n"
        f"Terms of Service:\n{tos_text}\n\n"
        "Extract the following fields as a JSON object with the following types:\n"
        "{\n"
        "  \"data_collected\": array of strings,  // types of data collected (max 100)\n"
        "  \"legal_compliance\": string,           // legal/compliance implications\n"
        "  \"published_subprocessors\": array of strings, // list of subprocessors (max 100)\n"
        "  \"s_and_c_cert\": array of strings,     // security and compliance certifications\n"
        "  \"bus_type\": array of strings,         // business type\n"
        "  \"alias\": array of strings,            // known aliases\n"
        "  \"compliance_certifications\": array of strings, // compliance certifications\n"
        "  \"risk_categories\": array of strings   // risk categories\n"
        "}\n"
        "Use only real, verifiable information. If a value does not exist, use an empty string for strings or an empty array for arrays."
    )
    llm_result = llm_json_response(prompt)
    # Fallback if LLM fails
    if not llm_result:
        llm_result = {
            "data_collected": [],
            "legal_compliance": "",
            "published_subprocessors": [],
            "s_and_c_cert": [],
            "bus_type": [],
            "alias": [],
            "compliance_certifications": [],
            "risk_categories": [],
            "date": datetime.now(tz=timezone.utc).date().isoformat()
        }
    elif isinstance(llm_result, dict):
        llm_result["date"] = datetime.now(tz=timezone.utc).date().isoformat()
    else:
        pass
    return llm_result

def get_security_and_risk_data(website_url):
    # Placeholder: Call third-party APIs for security_rating, risk_score, breach_history
    return {
        "security_rating": 10,
        "risk_score": 10,
        "breach_history": []
    }

def get_vendor_info_auto(vendor_name, update_all_fields=True):
    if update_all_fields:
        website_url = search_official_website(vendor_name)
        scraped = scrape_website_for_fields(website_url, vendor_name=vendor_name)
    else:
        # Try to fetch existing info from DB
        try:
            obj = VendorInfo.select().where(VendorInfo.vendor == vendor_name).first()
        except Exception as e:
            print(f"Error fetching vendor from DB: {e}")
            obj = None
        if obj:
            website_url = obj.website_url
            scraped = {
                "logo": obj.logo,
                "contact_email": obj.contact_email,
                "headquarters_location": obj.headquarters_location,
                "privacy_policy_url": obj.privacy_policy_url,
                "tos_url": obj.tos_url
            }
        else:
            website_url = search_official_website(vendor_name)
            scraped = scrape_website_for_fields(website_url, vendor_name=vendor_name)
    llm_fields = extract_fields_with_llm(
        scraped.get("privacy_policy_url"),
        scraped.get("tos_url"),
        website_url
    )
    security_data = get_security_and_risk_data(website_url)
    vendor_info = {
        "vendor": vendor_name,
        "website_url": website_url,
        "logo": scraped.get("logo", None),
        "contact_email": scraped.get("contact_email", None),
        "headquarters_location": scraped.get("headquarters_location", None),
        "privacy_policy_url": scraped.get("privacy_policy_url", None),
        "tos_url": scraped.get("tos_url", None),
        "data_collected": llm_fields.get("data_collected", None),
        "legal_compliance": llm_fields.get("legal_compliance", None),
        "published_subprocessors": llm_fields.get("published_subprocessors", None),
        "s_and_c_cert": llm_fields.get("s_and_c_cert", None),
        "bus_type": llm_fields.get("bus_type", None),
        "alias": llm_fields.get("alias", None),
        "compliance_certifications": llm_fields.get("compliance_certifications", None),
        "risk_categories": llm_fields.get("risk_categories", None),
        "date": llm_fields.get("date", datetime.now(tz=timezone.utc).date().isoformat()),
        "security_rating": security_data.get("security_rating", None),
        "risk_score": security_data.get("risk_score", None),
        "breach_history": security_data.get("breach_history", None),
        "last_reviewed": "2024-06-01T00:00:00Z"
    }
    return vendor_info