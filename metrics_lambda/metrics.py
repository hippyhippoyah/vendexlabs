import json
import uuid
import os
import requests
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from config import db
from models import (
    RSSFeed, VendorProfile, VendorList, VendorListVendor, 
    Account, User, AccountUser, Vendor
)

API_URL = "https://api.openai.com/v1/chat/completions"
API_KEY = os.getenv("API_KEY")


def get_user_email(event):
    claims = None
    authorizer = event['requestContext'].get('authorizer', {})
    if 'jwt' in authorizer and 'claims' in authorizer['jwt']:
        claims = authorizer['jwt']['claims']
    elif 'claims' in authorizer:
        claims = authorizer['claims']
    else:
        return None
    return claims.get('email')


def is_user_in_account(account_id, email):
    try:
        account_uuid = uuid.UUID(account_id) if isinstance(account_id, str) else account_id
        account = Account.get(Account.id == account_uuid)
        user = User.get(User.email == email)
        return AccountUser.select().where(
            (AccountUser.account == account) & (AccountUser.user == user)
        ).exists()
    except (Account.DoesNotExist, User.DoesNotExist, ValueError):
        return False


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
        print(f"OpenAI API call failed: {e}")
        return None


def get_recent_incidents(account_id, vendor_list_id, limit=5):
    """Get recent incidents from RSS feeds"""
    db.connect(reuse_if_open=True)
    try:
        query = RSSFeed.select().order_by(RSSFeed.published.desc())
        
        # If vendor_list_id is provided, filter by vendors in that list
        if vendor_list_id:
            try:
                account_uuid = uuid.UUID(account_id) if isinstance(account_id, str) else account_id
                account = Account.get(Account.id == account_uuid)
                vendor_list = VendorList.get(
                    (VendorList.id == uuid.UUID(vendor_list_id)) & 
                    (VendorList.account == account)
                )
                
                # Get vendor names from the vendor list
                vendor_names = [
                    v.vendor.name 
                    for v in VendorListVendor.select().where(
                        VendorListVendor.vendor_list == vendor_list
                    )
                ]
                
                if vendor_names:
                    # Filter RSS feeds by vendor names (using vendor field)
                    query = query.where(RSSFeed.vendor.in_(vendor_names))
            except (Account.DoesNotExist, VendorList.DoesNotExist, ValueError):
                pass
        
        # Limit results
        feeds = query.limit(limit)
        
        result = []
        for feed in feeds:
            result.append({
                'id': str(feed.id),
                'title': feed.title,
                'vendor': None,
                'vendor_name': feed.vendor,
                'product': feed.product,
                'published': feed.published.isoformat() if feed.published else None,
                'exploits': feed.exploits,
                'summary': feed.summary,
                'url': feed.url,
                'img': feed.img,
                'incident_type': feed.incident_type,
                'affected_service': feed.affected_service,
                'potentially_impacted_data': feed.potentially_impacted_data,
                'status': feed.status,
                'source': feed.source
            })
        
        return {
            'statusCode': 200,
            'body': json.dumps(result, default=str)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error fetching recent incidents: {str(e)}')
        }
    finally:
        db.close()


def get_vendors_from_list(account_id, vendor_list_name='master-list'):
    """Get vendors from a vendor list (defaults to master-list)"""
    db.connect(reuse_if_open=True)
    try:
        is_individual = isinstance(account_id, str) and account_id.lower() == 'individual'
        
        if is_individual:
            # User-level master-list
            # Note: We'll need email from the event, but for now we'll handle it in the handler
            return {
                'statusCode': 400,
                'body': json.dumps('Individual account requires email context')
            }
        else:
            # Account-level master-list
            account_uuid = uuid.UUID(account_id) if isinstance(account_id, str) else account_id
            account = Account.get(Account.id == account_uuid)
            vendor_list = VendorList.get(
                (VendorList.name == vendor_list_name) & 
                (VendorList.account == account)
            )
            
            # Get vendors from the list
            vendor_list_vendors = VendorListVendor.select().where(
                VendorListVendor.vendor_list == vendor_list
            )
            
            result = []
            for vlv in vendor_list_vendors:
                vendor_name = vlv.vendor.name
                # Try to get vendor profile for logo and website_url
                try:
                    vendor_profile = VendorProfile.get(VendorProfile.vendor == vendor_name)
                    result.append({
                        'id': str(vendor_profile.id),
                        'vendor': vendor_name,
                        'logo': vendor_profile.logo,
                        'website_url': vendor_profile.website_url
                    })
                except VendorProfile.DoesNotExist:
                    # If no profile exists, still return basic info
                    result.append({
                        'id': str(vlv.vendor.id),
                        'vendor': vendor_name,
                        'logo': None,
                        'website_url': None
                    })
            
            return {
                'statusCode': 200,
                'body': json.dumps(result, default=str)
            }
    except VendorList.DoesNotExist:
        return {
            'statusCode': 404,
            'body': json.dumps('Vendor list not found')
        }
    except Account.DoesNotExist:
        return {
            'statusCode': 404,
            'body': json.dumps('Account not found')
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error fetching vendors: {str(e)}')
        }
    finally:
        db.close()


def get_vendors_from_list_individual(email, vendor_list_name='master-list'):
    """Get vendors from user-level master-list"""
    db.connect(reuse_if_open=True)
    try:
        user = User.get(User.email == email)
        vendor_list = VendorList.get(
            (VendorList.name == vendor_list_name) &
            (VendorList.user == user) &
            (VendorList.account.is_null())
        )
        
        # Get vendors from the list
        vendor_list_vendors = VendorListVendor.select().where(
            VendorListVendor.vendor_list == vendor_list
        )
        
        result = []
        for vlv in vendor_list_vendors:
            vendor_name = vlv.vendor.name
            # Try to get vendor profile for logo and website_url
            try:
                vendor_profile = VendorProfile.get(VendorProfile.vendor == vendor_name)
                result.append({
                    'id': str(vendor_profile.id),
                    'vendor': vendor_name,
                    'logo': vendor_profile.logo,
                    'website_url': vendor_profile.website_url
                })
            except VendorProfile.DoesNotExist:
                # If no profile exists, still return basic info
                result.append({
                    'id': str(vlv.vendor.id),
                    'vendor': vendor_name,
                    'logo': None,
                    'website_url': None
                })
        
        return {
            'statusCode': 200,
            'body': json.dumps(result, default=str)
        }
    except User.DoesNotExist:
        return {
            'statusCode': 404,
            'body': json.dumps('User not found')
        }
    except VendorList.DoesNotExist:
        return {
            'statusCode': 404,
            'body': json.dumps('Vendor list not found')
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error fetching vendors: {str(e)}')
        }
    finally:
        db.close()


def get_dashboard_metrics(account_id):
    """Get dashboard metrics: activeAssessments, totalVendors, followedVendors"""
    db.connect(reuse_if_open=True)
    try:
        is_individual = isinstance(account_id, str) and account_id.lower() == 'individual'
        
        # Active assessments - set to 0 temporarily
        active_assessments = 0
        
        # Total vendors - count all vendors in VendorProfile table
        total_vendors = VendorProfile.select().count()
        
        # Followed vendors - count vendors in master-list
        if is_individual:
            # Will need email from event context
            return {
                'statusCode': 400,
                'body': json.dumps('Individual account requires email context')
            }
        else:
            account_uuid = uuid.UUID(account_id) if isinstance(account_id, str) else account_id
            account = Account.get(Account.id == account_uuid)
            vendor_list = VendorList.get(
                (VendorList.name == 'master-list') & 
                (VendorList.account == account)
            )
            followed_vendors = VendorListVendor.select().where(
                VendorListVendor.vendor_list == vendor_list
            ).count()
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'activeAssessments': active_assessments,
                'totalVendors': total_vendors,
                'followedVendors': followed_vendors
            })
        }
    except Account.DoesNotExist:
        return {
            'statusCode': 404,
            'body': json.dumps('Account not found')
        }
    except VendorList.DoesNotExist:
        # If master-list doesn't exist, return 0 for followed vendors
        total_vendors = VendorProfile.select().count()
        return {
            'statusCode': 200,
            'body': json.dumps({
                'activeAssessments': 0,
                'totalVendors': total_vendors,
                'followedVendors': 0
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error fetching dashboard metrics: {str(e)}')
        }
    finally:
        db.close()


def get_dashboard_metrics_individual(email):
    """Get dashboard metrics for individual account"""
    db.connect(reuse_if_open=True)
    try:
        # Active assessments - set to 0 temporarily
        active_assessments = 0
        
        # Total vendors - count all vendors in VendorProfile table
        total_vendors = VendorProfile.select().count()
        
        # Followed vendors - count vendors in user's master-list
        user = User.get(User.email == email)
        vendor_list = VendorList.get(
            (VendorList.name == 'master-list') &
            (VendorList.user == user) &
            (VendorList.account.is_null())
        )
        followed_vendors = VendorListVendor.select().where(
            VendorListVendor.vendor_list == vendor_list
        ).count()
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'activeAssessments': active_assessments,
                'totalVendors': total_vendors,
                'followedVendors': followed_vendors
            })
        }
    except User.DoesNotExist:
        return {
            'statusCode': 404,
            'body': json.dumps('User not found')
        }
    except VendorList.DoesNotExist:
        # If master-list doesn't exist, return 0 for followed vendors
        total_vendors = VendorProfile.select().count()
        return {
            'statusCode': 200,
            'body': json.dumps({
                'activeAssessments': 0,
                'totalVendors': total_vendors,
                'followedVendors': 0
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error fetching dashboard metrics: {str(e)}')
        }
    finally:
        db.close()


def get_ai_summary(account_id, vendor_list_id=None):
    """Generate AI weekly summary"""
    db.connect(reuse_if_open=True)
    try:
        # Get recent incidents from last 7 days
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        recent_feeds = RSSFeed.select().where(
            RSSFeed.published >= seven_days_ago
        ).order_by(RSSFeed.published.desc()).limit(20)
        
        # Get dashboard metrics directly (avoid nested db connections)
        is_individual = isinstance(account_id, str) and account_id.lower() == 'individual'
        if is_individual:
            return {
                'statusCode': 400,
                'body': json.dumps('Individual account requires email context')
            }
        
        # Calculate metrics directly
        active_assessments = 0
        total_vendors = VendorProfile.select().count()
        
        try:
            account_uuid = uuid.UUID(account_id) if isinstance(account_id, str) else account_id
            account = Account.get(Account.id == account_uuid)
            vendor_list = VendorList.get(
                (VendorList.name == 'master-list') & 
                (VendorList.account == account)
            )
            followed_vendors = VendorListVendor.select().where(
                VendorListVendor.vendor_list == vendor_list
            ).count()
        except (Account.DoesNotExist, VendorList.DoesNotExist):
            followed_vendors = 0
        
        metrics_data = {
            'activeAssessments': active_assessments,
            'totalVendors': total_vendors,
            'followedVendors': followed_vendors
        }
        
        # Build context for AI summary
        incidents_summary = []
        for feed in recent_feeds:
            incidents_summary.append({
                'vendor': feed.vendor,
                'product': feed.product,
                'title': feed.title,
                'summary': feed.summary,
                'incident_type': feed.incident_type,
                'status': feed.status,
                'published': feed.published.isoformat() if feed.published else None
            })
        
        # Create prompt for OpenAI
        prompt = f"""Generate a weekly vendor risk summary based on the following information:

Dashboard Metrics:
- Active Assessments: {metrics_data.get('activeAssessments', 0)}
- Total Vendors: {metrics_data.get('totalVendors', 0)}
- Followed Vendors: {metrics_data.get('followedVendors', 0)}

Recent Incidents (Last 7 Days):
{json.dumps(incidents_summary, indent=2)}

Please provide a concise weekly summary (2-3 sentences) highlighting key developments, risk levels, and any vendors requiring immediate attention. Focus on the most significant incidents and overall risk assessment."""

        messages = [
            {"role": "user", "content": prompt}
        ]
        
        summary = call_openai_api(messages, max_tokens=500, temperature=0.7)
        
        if not summary:
            return {
                'statusCode': 500,
                'body': json.dumps('Failed to generate AI summary')
            }
        
        return {
            'statusCode': 200,
            'body': json.dumps(summary)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error generating AI summary: {str(e)}')
        }
    finally:
        db.close()


def get_ai_summary_individual(email, vendor_list_id=None):
    """Generate AI weekly summary for individual account"""
    db.connect(reuse_if_open=True)
    try:
        # Get recent incidents from last 7 days
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        recent_feeds = RSSFeed.select().where(
            RSSFeed.published >= seven_days_ago
        ).order_by(RSSFeed.published.desc()).limit(20)
        
        # Calculate metrics directly (avoid nested db connections)
        active_assessments = 0
        total_vendors = VendorProfile.select().count()
        
        try:
            user = User.get(User.email == email)
            vendor_list = VendorList.get(
                (VendorList.name == 'master-list') &
                (VendorList.user == user) &
                (VendorList.account.is_null())
            )
            followed_vendors = VendorListVendor.select().where(
                VendorListVendor.vendor_list == vendor_list
            ).count()
        except (User.DoesNotExist, VendorList.DoesNotExist):
            followed_vendors = 0
        
        metrics_data = {
            'activeAssessments': active_assessments,
            'totalVendors': total_vendors,
            'followedVendors': followed_vendors
        }
        
        # Build context for AI summary
        incidents_summary = []
        for feed in recent_feeds:
            incidents_summary.append({
                'vendor': feed.vendor,
                'product': feed.product,
                'title': feed.title,
                'summary': feed.summary,
                'incident_type': feed.incident_type,
                'status': feed.status,
                'published': feed.published.isoformat() if feed.published else None
            })
        
        # Create prompt for OpenAI
        prompt = f"""Generate a weekly vendor risk summary based on the following information:

Dashboard Metrics:
- Active Assessments: {metrics_data.get('activeAssessments', 0)}
- Total Vendors: {metrics_data.get('totalVendors', 0)}
- Followed Vendors: {metrics_data.get('followedVendors', 0)}

Recent Incidents (Last 7 Days):
{json.dumps(incidents_summary, indent=2)}

Please provide a concise weekly summary (2-3 sentences) highlighting key developments, risk levels, and any vendors requiring immediate attention. Focus on the most significant incidents and overall risk assessment."""

        messages = [
            {"role": "user", "content": prompt}
        ]
        
        summary = call_openai_api(messages, max_tokens=500, temperature=0.7)
        
        if not summary:
            return {
                'statusCode': 500,
                'body': json.dumps('Failed to generate AI summary')
            }
        
        return {
            'statusCode': 200,
            'body': json.dumps(summary)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error generating AI summary: {str(e)}')
        }
    finally:
        db.close()


def lambda_handler(event, context):
    """Main lambda handler with path-based routing"""
    # Get authentication
    email = get_user_email(event)
    if not email:
        return {'statusCode': 401, 'body': json.dumps('Unauthorized')}
    
    # Get HTTP method
    method = event.get('requestContext', {}).get('http', {}).get('method', 'GET')
    if method.upper() != 'GET':
        return {'statusCode': 405, 'body': json.dumps('Method Not Allowed')}
    
    # Parse path from rawPath (for proxy routes) or routeKey
    raw_path = event.get('rawPath', '')
    route_key = event.get('routeKey', '')
    
    # Extract the endpoint path after /metrics/
    endpoint = None
    if raw_path:
        # Handle paths like /test/metrics/recent-incidents or /metrics/recent-incidents
        parts = raw_path.strip('/').split('/')
        if 'metrics' in parts:
            metrics_index = parts.index('metrics')
            if metrics_index + 1 < len(parts):
                endpoint = parts[metrics_index + 1]
        elif raw_path.startswith('/metrics/'):
            endpoint = raw_path.replace('/metrics/', '').split('?')[0]
    elif route_key and route_key != f'GET /metrics/{{proxy+}}':
        # Fallback to routeKey if it's not a proxy pattern
        if route_key.startswith('GET /metrics/'):
            endpoint = route_key.replace('GET /metrics/', '').split('?')[0]
    
    if not endpoint:
        return {'statusCode': 400, 'body': json.dumps('Invalid path: could not extract endpoint')}
    
    # Get query parameters
    query_params = event.get('queryStringParameters') or {}
    account_id = query_params.get('account-id')
    vendor_list_id = query_params.get('vendor-list-id')
    vendor_list_name = query_params.get('vendor-list-name', 'master-list')
    limit = int(query_params.get('limit', 5))
    
    if not account_id:
        return {'statusCode': 400, 'body': json.dumps("Missing 'account-id' parameter")}
    
    is_individual = isinstance(account_id, str) and account_id.lower() == 'individual'
    
    # Validate account access (unless individual)
    if not is_individual:
        if not is_user_in_account(account_id, email):
            return {'statusCode': 403, 'body': json.dumps('Forbidden: Not authorized for this account')}
    
    # Route to appropriate endpoint based on parsed path
    if endpoint == 'recent-incidents':
        return get_recent_incidents(account_id, vendor_list_id, limit)
    
    elif endpoint == 'vendors-from-list':
        if is_individual:
            return get_vendors_from_list_individual(email, vendor_list_name)
        else:
            return get_vendors_from_list(account_id, vendor_list_name)
    
    elif endpoint == 'dashboard':
        if is_individual:
            return get_dashboard_metrics_individual(email)
        else:
            return get_dashboard_metrics(account_id)
    
    elif endpoint == 'ai-summary':
        if is_individual:
            return get_ai_summary_individual(email, vendor_list_id)
        else:
            return get_ai_summary(account_id, vendor_list_id)
    
    else:
        return {'statusCode': 404, 'body': json.dumps(f'Endpoint not found: {endpoint}')}

