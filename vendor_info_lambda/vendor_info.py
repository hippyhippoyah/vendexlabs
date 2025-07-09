import json
from cleanco import basename
from config import db
from models import VendorInfo
import os
from vendor_utils import get_vendor_info_auto
import uuid

def add_info_to_db(vendors, update_all_fields=True):
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
        obj = VendorInfo.select().where(VendorInfo.vendor == normalized_vendor).first()
        if obj:
            vendor_info = get_vendor_info_auto(normalized_vendor, update_all_fields=update_all_fields)
        else:
            vendor_info = get_vendor_info_auto(normalized_vendor, update_all_fields=True)
        print("Vendor info:", vendor_info)
        if not vendor_info:
            print(f"Could not generate info for {normalized_vendor}")
            continue

        try:
            if obj:
                # Only update fields that are not None
                if vendor_info.get('s_and_c_cert') is not None:
                    obj.s_and_c_cert = vendor_info.get('s_and_c_cert', [])
                if vendor_info.get('bus_type') is not None:
                    obj.bus_type = vendor_info.get('bus_type', [])
                if vendor_info.get('data_collected') is not None:
                    obj.data_collected = vendor_info.get('data_collected') if vendor_info.get('data_collected') not in ("", None) else None
                if vendor_info.get('legal_compliance') is not None:
                    obj.legal_compliance = vendor_info.get('legal_compliance') if vendor_info.get('legal_compliance') not in ("", None) else None
                if vendor_info.get('published_subprocessors') is not None:
                    obj.published_subprocessors = vendor_info.get('published_subprocessors', [])
                if vendor_info.get('privacy_policy_url') is not None:
                    obj.privacy_policy_url = vendor_info.get('privacy_policy_url')
                if vendor_info.get('terms_of_service_url') is not None or vendor_info.get('tos_url') is not None:
                    obj.tos_url = vendor_info.get('terms_of_service_url') or vendor_info.get('tos_url')
                if vendor_info.get('date') is not None:
                    obj.date = vendor_info.get('date')
                if vendor_info.get('alias') is not None:
                    obj.alias = vendor_info.get('alias')
                if vendor_info.get('logo') is not None:
                    obj.logo = vendor_info.get('logo')
                if vendor_info.get('data') is not None:
                    obj.data = vendor_info.get('data')
                if vendor_info.get('security_rating') is not None:
                    obj.security_rating = vendor_info.get('security_rating')
                if vendor_info.get('risk_score') is not None:
                    obj.risk_score = vendor_info.get('risk_score')
                if vendor_info.get('risk_categories') is not None:
                    obj.risk_categories = vendor_info.get('risk_categories')
                if vendor_info.get('compliance_certifications') is not None:
                    obj.compliance_certifications = vendor_info.get('compliance_certifications')
                if vendor_info.get('headquarters_location') is not None:
                    obj.headquarters_location = vendor_info.get('headquarters_location')
                if vendor_info.get('contact_email') is not None:
                    obj.contact_email = vendor_info.get('contact_email')
                if vendor_info.get('breach_history') is not None:
                    obj.breach_history = vendor_info.get('breach_history')
                if vendor_info.get('last_reviewed') is not None:
                    obj.last_reviewed = vendor_info.get('last_reviewed')
                if vendor_info.get('website_url') is not None:
                    obj.website_url = vendor_info.get('website_url')
                obj.save()
                updated_vendors.append(normalized_vendor)
            else:
                obj = VendorInfo.create(
                    vendor=normalized_vendor,
                    s_and_c_cert=vendor_info.get('s_and_c_cert', []),
                    bus_type=vendor_info.get('bus_type', []),
                    data_collected=vendor_info.get('data_collected') if vendor_info.get('data_collected') not in ("", None) else None,
                    legal_compliance=vendor_info.get('legal_compliance') if vendor_info.get('legal_compliance') not in ("", None) else None,
                    published_subprocessors=vendor_info.get('published_subprocessors', []),
                    privacy_policy_url=vendor_info.get('privacy_policy_url'),
                    tos_url=vendor_info.get('terms_of_service_url') or vendor_info.get('tos_url'),
                    date=vendor_info.get('date'),
                    alias=vendor_info.get('alias'),
                    logo=vendor_info.get('logo'),
                    data=vendor_info.get('data'),
                    security_rating=vendor_info.get('security_rating'),
                    risk_score=vendor_info.get('risk_score'),
                    risk_categories=vendor_info.get('risk_categories'),
                    compliance_certifications=vendor_info.get('compliance_certifications'),
                    headquarters_location=vendor_info.get('headquarters_location'),
                    contact_email=vendor_info.get('contact_email'),
                    breach_history=vendor_info.get('breach_history'),
                    last_reviewed=vendor_info.get('last_reviewed'),
                    website_url=vendor_info.get('website_url')
                )
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
                    "alias": obj.alias,
                    "logo": obj.logo,
                    "data": obj.data,
                    "security_rating": obj.security_rating,
                    "risk_score": obj.risk_score,
                    "risk_categories": obj.risk_categories,
                    "compliance_certifications": obj.compliance_certifications,
                    "headquarters_location": obj.headquarters_location,
                    "contact_email": obj.contact_email,
                    "breach_history": obj.breach_history,
                    "last_reviewed": obj.last_reviewed,
                    "website_url": obj.website_url
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
        for obj in VendorInfo.select(VendorInfo.id, VendorInfo.vendor, VendorInfo.logo, VendorInfo.website_url):
            results.append({
                "id": str(obj.id),
                "vendor": obj.vendor,
                "logo": obj.logo,
                "website_url": obj.website_url
            })
    except Exception as e:
        print(f"Error querying all vendors: {e}")
    db.close()
    return {
        'statusCode': 200,
        'body': json.dumps(results, default=str)
    }

def get_vendor_info_by_id_or_name(id=None, vendor_name=None):
    """
    Retrieve vendor info by id or vendor_name.
    """
    db.connect(reuse_if_open=True)
    obj = None
    try:
        if id is not None:
            obj = VendorInfo.select().where(VendorInfo.id == id).first()
        elif vendor_name is not None:
            normalized_vendor = basename(vendor_name).upper()
            obj = VendorInfo.select().where(VendorInfo.vendor == normalized_vendor).first()
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
                "alias": obj.alias,
                "logo": obj.logo,
                "data": obj.data,
                "security_rating": obj.security_rating,
                "risk_score": obj.risk_score,
                "risk_categories": obj.risk_categories,
                "compliance_certifications": obj.compliance_certifications,
                "headquarters_location": obj.headquarters_location,
                "contact_email": obj.contact_email,
                "breach_history": obj.breach_history,
                "last_reviewed": obj.last_reviewed,
                "website_url": obj.website_url
            }
            result = {
                'statusCode': 200,
                'body': json.dumps(vendor_info, default=str)
            }
        else:
            result = {
                'statusCode': 404,
                'body': json.dumps('Vendor not found')
            }
    except Exception as e:
        print(f"Error querying vendor by id or name: {e}")
        result = {
            'statusCode': 500,
            'body': json.dumps('Internal server error')
        }
    db.close()
    return result

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
    if route_key.startswith('GET /vendor/'):
        # Expecting /vendor/{id_or_name}
        id_or_name = None
        # Try to get from pathParameters (API Gateway proxy integration)
        if 'pathParameters' in event and event['pathParameters']:
            id_or_name = event['pathParameters'].get('id_or_name')
        # Fallback: parse from the path if pathParameters is not set
        if not id_or_name:
            path = event.get('rawPath') or event.get('path', '')
            # path should be like /vendor/{id_or_name}
            parts = path.strip('/').split('/')
            if len(parts) >= 2 and parts[0] == 'vendor':
                id_or_name = parts[1]
        # Try to parse as UUID, else treat as vendor_name
        vendor_id = None
        vendor_name = None
        try:
            vendor_id = uuid.UUID(id_or_name)
        except Exception:
            vendor_name = id_or_name
        return get_vendor_info_by_id_or_name(id=vendor_id, vendor_name=vendor_name)
    if route_key.startswith('POST '):
        body = event.get('body')
        if body:
            data = json.loads(body) if isinstance(body, str) else body
        else:
            data = event
        vendors = data.get('vendors', [])
        update_all_fields = data.get('updateAllFields', True)
        return add_info_to_db(vendors, update_all_fields=update_all_fields)
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


