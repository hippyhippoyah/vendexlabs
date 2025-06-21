import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import os
import json

def find_policy_urls(base_url):
    try:
        resp = requests.get(base_url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        privacy_urls = set()
        tos_urls = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            href_lower = href.lower()
            full_url = urljoin(base_url, href)
            if "privacy" in href_lower:
                privacy_urls.add(full_url)
            if "terms" in href_lower or "tos" in href_lower or "conditions" in href_lower:
                tos_urls.add(full_url)
        return {
            "privacy_policy_url": sorted(privacy_urls)[0] if privacy_urls else "",
            "terms_of_service_url": sorted(tos_urls)[0] if tos_urls else ""
        }
    except Exception as e:
        print(f"Error finding policy URLs for {base_url}: {e}")
        return {
            "privacy_policy_url": "",
            "terms_of_service_url": ""
        }

API_URL = "https://api.openai.com/v1/chat/completions"
API_KEY = os.getenv("API_KEY")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
GOOGLE_SEARCH_URL = "https://www.googleapis.com/customsearch/v1"

def google_custom_search(query, **kwargs):
    """
    Perform a Google Custom Search using the provided query.
    Additional parameters can be passed as keyword arguments.
    Returns the link of the first search result.
    """
    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        raise ValueError("Google API key or CSE ID not set in environment variables.")

    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CSE_ID,
        "q": query,
    }
    params.update(kwargs)
    response = requests.get(GOOGLE_SEARCH_URL, params=params)
    response.raise_for_status()
    results = response.json()
    # Return the link of the first result if available
    if "items" in results and len(results["items"]) > 0:
        return results["items"][0].get("link", "")
    return ""

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
        ],
        "max_tokens": 512,
        "temperature": 0
    }
    response = requests.post(API_URL, headers=headers, json=data)
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    try:
        json_start = content.find('{')
        if json_start != -1:
            content = content[json_start:]
        return json.loads(content)
    except Exception as e:
        print(f"Failed to parse JSON from model: {e}\nRaw content: {content}")
        return None
    
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
        "model": "gpt-4o-mini-search-preview",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
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

