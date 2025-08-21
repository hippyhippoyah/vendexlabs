import json
import requests
import time
import os
from datetime import datetime, timezone

GOOGLE_SEARCH_URL = os.getenv("GOOGLE_SEARCH_URL", "https://www.googleapis.com/customsearch/v1")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
PERPLEXITY_API_URL = os.getenv("PERPLEXITY_API_URL", "https://api.perplexity.ai/chat/completions")
print("Using Perplexity API KEY:", PERPLEXITY_API_KEY)

total_tokens_used = 0


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
    query = f"{vendor_name} official website"
    return google_custom_search(query)

def perplexity_json_response(prompt, model="sonar", response_format=None):
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 2000,
        "top_p": 0.5,
        "web_search_options": {
            "search_context_size": "medium"
        }
    }
    if response_format:
        payload["response_format"] = response_format
    try:
        response = requests.post(PERPLEXITY_API_URL, json=payload, headers=headers)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        raise
    resp_json = response.json()
    if 'usage' in resp_json:
        usage = resp_json['usage']
        tokens_used = usage.get('total_tokens', 0)
        global total_tokens_used
        total_tokens_used += tokens_used
    import re
    try:
        choices = resp_json.get("choices", [])
        # Optionally print search results for debugging
        # print(json.dumps(resp_json.get("search_results", []), indent=2))
        if choices:
            content = choices[0].get("message", {}).get("content", "")
            if content:
                # Remove bracketed references like [1][3][5]
                content_clean = re.sub(r"\s*\[\d+\]", "", content)
                try:
                    return json.loads(content_clean)
                except json.JSONDecodeError:
                    return None
        return None
    except (KeyError, IndexError):
        return None

def get_vendor_logo(vendor_name, website_url=None):
    query = f"{vendor_name} logo"
    logo_url = google_custom_search(query, search_type="image")
    if not logo_url and website_url:
        logo_url = google_custom_search(f"{website_url} logo", search_type="image")
    return logo_url

def get_security_and_risk_data(website_url):
    return {
        "security_rating": 10,
        "risk_score": 10,
        "breach_history": [],
        "risk_categories": ["data_processing", "third_party_sharing"]
    }

def gather_additional_vendor_info(vendor_name, website_url=None, model="sonar"):
    prompt = (
        f"For the company {vendor_name}, find the following information:\n"
        f"Website URL context: {website_url or 'Not provided'}\n"
        "- alias: Known alternative names or aliases for the company (list)\n"
        "- privacy_policy_url: Direct URL to their privacy policy\n"
        "- tos_url: Direct URL to their terms of service\n"
        "- contact_email: Primary contact email address\n"
        "- data_collected: Types of data they typically collect from users (list)\n"
        "If URLs are not found, use a best guess. If information not available, use appropriate defaults."
    )
    
    response_format = {
        'type': 'json_schema',
        'json_schema': {
            'schema': {
                'type': 'object',
                'properties': {
                    'alias': {'type': 'array', 'items': {'type': 'string'}},
                    'privacy_policy_url': {'type': 'string'},
                    'tos_url': {'type': 'string'},
                    'contact_email': {'type': 'string'},
                    'data_collected': {'type': 'array', 'items': {'type': 'string'}}
                },
                'required': ['alias', 'privacy_policy_url', 'tos_url', 'contact_email', 'data_collected']
            }
        }
    }
    
    return perplexity_json_response(prompt, model=model, response_format=response_format)
def gather_basic_company_info(vendor_name, model="sonar"):
    prompt = (
        f"Given the company {vendor_name}, extract the following basic information:\n"
        "- company_description: Brief description of what the company does\n"
        "- business_type: Whether they serve 'B2B', 'B2C', or 'Government' customers\n"
        "- founded_year: Year the company was founded (number or null if unknown)\n"
        "- employee_count: Current number of employees (number or null if unknown)\n"
        "- industry: Primary industry sector\n"
        "- primary_product: Main product or service offering\n"
        "- headquarters_location: City and country of headquarters\n"
        "- website_url: Official company website URL\n\n"
        "For employee_count, look for recent headcount information, LinkedIn employee estimates, "
        "or company size data from business databases. If no specific number is available, use null.\n"
        "Provide accurate factual data only. If information is not available, use null. DO NOT MAKE UP INFORMATION"
    )
    response_format = {
        'type': 'json_schema',
        'json_schema': {
            'schema': {
                'type': 'object',
                'properties': {
                    'company_description': {'type': 'string'},
                    'business_type': {'type': 'string', 'enum': ['B2B', 'B2C', 'Government']},
                    'founded_year': {'type': ['number', 'null']},
                    'employee_count': {'type': ['number', 'null']},
                    'industry': {'type': 'string'},
                    'primary_product': {'type': 'string'},
                    'headquarters_location': {'type': 'string'},
                    'website_url': {'type': 'string'}
                },
                'required': ['company_description', 'business_type', 'founded_year', 'employee_count', 'industry', 'primary_product', 'headquarters_location', 'website_url']
            }
        }
    }
    return perplexity_json_response(prompt, model=model, response_format=response_format)

def gather_business_maturity_info(vendor_name, model="sonar"):
    prompt = (
        f"For the company {vendor_name}, provide business maturity information:\n"
        "- company_type: 'Private' or 'Public'\n"
        "- total_funding: Total funding raised in USD (use 0 if unknown)\n"
        "- funding_round: Latest funding round (e.g., 'Series A', 'IPO', 'Bootstrap')\n"
        "- has_enterprise_customers: Does the company serve enterprise clients?\n"
        "- popularity_index: Rate popularity from 1-100 based on market presence\n"
        "- revenue_estimate: Estimated annual revenue in USD (use 0 if unknown)\n"
        "- customer_count_estimate: Estimated number of customers (use 0 if unknown)\n"
        "Provide factual information where available, reasonable estimates otherwise."
    )
    
    response_format = {
        'type': 'json_schema',
        'json_schema': {
            'schema': {
                'type': 'object',
                'properties': {
                    'company_type': {'type': 'string', 'enum': ['Private', 'Public']},
                    'total_funding': {'type': 'number'},
                    'funding_round': {'type': 'string'},
                    'has_enterprise_customers': {'type': 'boolean'},
                    'popularity_index': {'type': 'number', 'minimum': 1, 'maximum': 100},
                    'revenue_estimate': {'type': 'number'},
                    'customer_count_estimate': {'type': 'number'}
                },
                'required': ['company_type', 'total_funding', 'funding_round', 'has_enterprise_customers', 'popularity_index', 'revenue_estimate', 'customer_count_estimate']
            }
        }
    }
    
    return perplexity_json_response(prompt, model=model, response_format=response_format)

def gather_security_compliance_info(vendor_name, model="sonar"):
    prompt = (
        f"For the company {vendor_name}, provide security and compliance information:\n"
        "- compliance_certifications: List of security certifications (SOC2, ISO27001, etc.)\n"
        "- published_subprocessors: List of known third-party processors/partners\n"
        "Research their public security documentation and certifications."
    )
    
    response_format = {
        'type': 'json_schema',
        'json_schema': {
            'schema': {
                'type': 'object',
                'properties': {
                    'compliance_certifications': {'type': 'array', 'items': {'type': 'string'}},
                    'published_subprocessors': {'type': 'array', 'items': {'type': 'string'}}
                },
                'required': ['compliance_certifications', 'published_subprocessors']
            }
        }
    }
    
    return perplexity_json_response(prompt, model=model, response_format=response_format)

def gather_privacy_controls_info(vendor_name, model="sonar"):
    prompt = (
        f"For the company {vendor_name}, provide data privacy and handling information:\n"
        "- shared_data_description: How they share data with third parties\n"
        "- ml_training_data_description: How they use data for ML/AI training\n"
        "- supports_data_subject_requests: Do they support GDPR data subject requests?\n"
        "- gdpr_compliant: Are they GDPR compliant?\n"
        "- data_returned_after_termination: Do they return data after contract termination?\n"
        "- data_physical_location: Where is data physically stored?\n"
        "Base answers on their privacy policy and public documentation."
    )
    
    response_format = {
        'type': 'json_schema',
        'json_schema': {
            'schema': {
                'type': 'object',
                'properties': {
                    'shared_data_description': {'type': 'string'},
                    'ml_training_data_description': {'type': 'string'},
                    'supports_data_subject_requests': {'type': 'boolean'},
                    'gdpr_compliant': {'type': 'boolean'},
                    'data_returned_after_termination': {'type': 'boolean'},
                    'data_physical_location': {'type': 'string'}
                },
                'required': ['shared_data_description', 'ml_training_data_description', 'supports_data_subject_requests', 'gdpr_compliant', 'data_returned_after_termination', 'data_physical_location']
            }
        }
    }
    
    return perplexity_json_response(prompt, model=model, response_format=response_format)

def gather_vendor_data(vendor_name, website_url=None, model="sonar"):
    result = {
        'vendors': {
            'vendor': vendor_name,
            'date': datetime.now(timezone.utc).strftime('%Y-%m-%d'),
            'last_reviewed': datetime.now(timezone.utc).isoformat()
        },
        'vendor_security': {},
        'privacy_controls': {},
        'business_maturity': {}
    }
    
    basic_info = gather_basic_company_info(vendor_name, model=model)
    if basic_info:
        result['vendors'].update(basic_info)
        if not website_url:
            website_url = basic_info.get('website_url', '')
    else:
        print("  - WARNING: Failed to gather basic company info")
    
    maturity_info = gather_business_maturity_info(vendor_name, model=model)
    if maturity_info:
        result['vendors']['customer_count_estimate'] = maturity_info.pop('customer_count_estimate', 0)
        result['business_maturity'] = maturity_info
    else:
        print("  - WARNING: Failed to gather business maturity info")
    
    security_info = gather_security_compliance_info(vendor_name, model=model)
    if security_info:
        result['vendor_security'] = security_info
    else:
        print("  - WARNING: Failed to gather security compliance info")
    
    privacy_info = gather_privacy_controls_info(vendor_name, model=model)
    if privacy_info:
        result['privacy_controls'] = privacy_info
    else:
        print("  - WARNING: Failed to gather privacy controls info")
    
    time.sleep(2)
    
    additional_info = gather_additional_vendor_info(vendor_name, website_url, model=model)
    if additional_info:
        result['vendors'].update(additional_info)
    else:
        print("  - WARNING: Failed to gather additional vendor info")
    
    result['vendors']['logo'] = get_vendor_logo(vendor_name, website_url)
    
    security_risk = get_security_and_risk_data(website_url)
    result['vendors'].update(security_risk)
    
    current_time = datetime.now(timezone.utc).isoformat()
    result['vendor_security']['created_at'] = current_time
    result['vendor_security']['updated_at'] = current_time
    result['privacy_controls']['created_at'] = current_time
    result['privacy_controls']['updated_at'] = current_time
    result['business_maturity']['created_at'] = current_time
    result['business_maturity']['updated_at'] = current_time
    
    print(f"  - Total tokens used in this session: {total_tokens_used}")
    return result