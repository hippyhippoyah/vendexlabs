import json
from cleanco import basename
from config import db
from models import VendorInfo
import os
from vendor_utils import generate_vendor_info

API_URL = "https://api.openai.com/v1/chat/completions"
API_KEY = os.getenv("API_KEY")

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

        normalized_vendor = basename(vendor).upper()
        vendor_info = generate_vendor_info(normalized_vendor)
        if not vendor_info:
            print(f"Could not generate info for {normalized_vendor}")
            continue

        try:
            obj, created = VendorInfo.get_or_create(
                vendor=normalized_vendor,
                defaults={
                    "s_and_c_cert": vendor_info.get('s_and_c_cert', []),
                    "bus_type": vendor_info.get('bus_type', []),
                    "data_collected": vendor_info.get('data_collected'),
                    "legal_compliance": vendor_info.get('legal_compliance'),
                    "published_subprocessors": vendor_info.get('published_subprocessors', []),
                    "privacy_policy_url": vendor_info.get('privacy_policy_url'),
                    "tos_url": vendor_info.get('terms_of_service_url'),
                    "date": vendor_info.get('date'),
                    "alias": vendor_info.get('alias')
                }
            )
            if not created:
                # Update the existing vendor's information
                obj.s_and_c_cert = vendor_info.get('s_and_c_cert', [])
                obj.bus_type = vendor_info.get('bus_type', [])
                obj.data_collected = vendor_info.get('data_collected')
                obj.legal_compliance = vendor_info.get('legal_compliance')
                obj.published_subprocessors = vendor_info.get('published_subprocessors', [])
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
                    "s_and_c_cert": obj.s_and_c_cert if obj.s_and_c_cert else [],
                    "bus_type": obj.bus_type if obj.bus_type else [],
                    "data_collected": obj.data_collected,
                    "legal_compliance": obj.legal_compliance,
                    "published_subprocessors": obj.published_subprocessors if obj.published_subprocessors else [],
                    "privacy_policy_url": obj.privacy_policy_url,
                    "tos_url": obj.tos_url,
                    "date": obj.date,
                    "alias": obj.alias
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

def get_all_vendors_from_db():
    db.connect(reuse_if_open=True)
    results = []
    try:
        for obj in VendorInfo.select(VendorInfo.vendor):
            results.append(obj.vendor)
    except Exception as e:
        print(f"Error querying all vendors: {e}")
    db.close()
    return {
        'statusCode': 200,
        'body': json.dumps(results, default=str)
    }

def lambda_handler(event, context):
    try:
        route_key = event.get('routeKey', '')
    except Exception:
        return {
            'statusCode': 400,
            'body': json.dumps('Bad Request: No routeKey found')
        }
    if route_key == 'GET /vendors/all':
        return get_all_vendors_from_db()
    if route_key.startswith('POST '):
        body = event.get('body')
        if body:
            data = json.loads(body) if isinstance(body, str) else body
        else:
            data = event
        vendors = data.get('vendors', [])
        return add_info_to_db(vendors)
    elif route_key.startswith('GET '):
        vendor_names = event.get('queryStringParameters', {}).get('vendors', [])
        print(f"Vendor names: {vendor_names}")
        if isinstance(vendor_names, str):
            vendor_names = [v.strip() for v in vendor_names.split(',')]
        return get_vendor_info_from_db(vendor_names)
    else:
        return {
            'statusCode': 400,
            'body': json.dumps('Bad Request: Invalid routeKey')
        }


