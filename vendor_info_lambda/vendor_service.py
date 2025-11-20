import json
import uuid
from datetime import datetime
from pathlib import Path

from cleanco import basename

# Support running when this module is executed directly or imported dynamically.
try:
    from config import db
    from models import (
        VendorProfile,
        VendorSecurity,
        PrivacyControls,
        BusinessMaturity,
        RSSFeed,
    )
    from vendor_utils import gather_vendor_data
except ImportError:
    # When executed directly, ensure project root is on sys.path
    import sys

    ROOT_DIR = Path(__file__).resolve().parents[1]
    if str(ROOT_DIR) not in sys.path:
        sys.path.append(str(ROOT_DIR))
    from config import db  # type: ignore
    from models import (  # type: ignore
        VendorProfile,
        VendorSecurity,
        PrivacyControls,
        BusinessMaturity,
        RSSFeed,
    )
    from vendor_utils import gather_vendor_data  # type: ignore


def is_admin_claim(event):
    print("Full event for debugging:", json.dumps(event, indent=2))
    claims = None
    authorizer = event['requestContext'].get('authorizer', {})
    if 'jwt' in authorizer and 'claims' in authorizer['jwt']:
        claims = authorizer['jwt']['claims']
    elif 'claims' in authorizer:
        claims = authorizer['claims']
    else:
        print("No claims found in authorizer")
        return False
    groups = claims.get('cognito:groups', [])
    print(f"User groups from claims: {groups}")
    if isinstance(groups, str):
        groups = [g.strip() for g in groups.split(',')]
    return any('Admins' in g for g in groups)


def update_or_create_vendor(vendor_name, update_all_fields=True, model="sonar"):
    """Simple function to update or create vendor with all related data"""
    normalized_vendor = basename(vendor_name).upper()

    # Get vendor data
    vendor_data = gather_vendor_data(normalized_vendor, model=model)
    if not vendor_data or 'vendors' not in vendor_data:
        return None, f"Could not generate info for {normalized_vendor}"

    vendor_info = vendor_data['vendors']

    # Update or create main vendor record
    vendor, created = VendorProfile.get_or_create(
        vendor=normalized_vendor,
        defaults=vendor_info
    )

    if not created and update_all_fields:
        # Update existing vendor
        for field, value in vendor_info.items():
            if hasattr(vendor, field) and value is not None:
                setattr(vendor, field, value)
        vendor.updated_at = datetime.now()
        vendor.save()

    # Handle related records
    _update_related_records(vendor, vendor_data)

    return vendor, "updated" if not created else "created"


def _update_related_records(vendor, vendor_data):
    """Helper to update related security, privacy, and maturity records"""
    # Security info
    if 'vendor_security' in vendor_data and vendor_data['vendor_security']:
        VendorSecurity.delete().where(VendorSecurity.vendor == vendor).execute()
        VendorSecurity.create(vendor=vendor, **vendor_data['vendor_security'])

    # Privacy info
    if 'privacy_controls' in vendor_data and vendor_data['privacy_controls']:
        PrivacyControls.delete().where(PrivacyControls.vendor == vendor).execute()
        PrivacyControls.create(vendor=vendor, **vendor_data['privacy_controls'])

    # Maturity info
    if 'business_maturity' in vendor_data and vendor_data['business_maturity']:
        BusinessMaturity.delete().where(BusinessMaturity.vendor == vendor).execute()
        BusinessMaturity.create(vendor=vendor, **vendor_data['business_maturity'])


def get_complete_vendor_info(vendor_obj):
    """Get vendor with all related data in one place"""
    # Base vendor info
    vendor_dict = {
        "id": str(vendor_obj.id),
        "vendor": vendor_obj.vendor,
        **{field: getattr(vendor_obj, field) for field in [
            'company_description', 'business_type', 'founded_year', 'employee_count',
            'industry', 'primary_product', 'customer_count_estimate', 'logo',
            'website_url', 'privacy_policy_url', 'tos_url', 'headquarters_location',
            'contact_email', 'security_rating', 'risk_score', 'date', 'last_reviewed'
        ]},
        # Handle JSON fields with defaults
        "alias": vendor_obj.alias or [],
        "data_collected": vendor_obj.data_collected or [],
        "risk_categories": vendor_obj.risk_categories or [],
        "breach_history": vendor_obj.breach_history or [],
    }

    # Add related data using Peewee's backref relationships
    if hasattr(vendor_obj, 'security_info') and vendor_obj.security_info:
        security = vendor_obj.security_info[0]  # get first related record
        vendor_dict.update({
            "compliance_certifications": security.compliance_certifications or [],
            "published_subprocessors": security.published_subprocessors or []
        })

    if hasattr(vendor_obj, 'privacy_controls') and vendor_obj.privacy_controls:
        privacy = vendor_obj.privacy_controls[0]
        vendor_dict.update({
            "shared_data_description": privacy.shared_data_description,
            "ml_training_data_description": privacy.ml_training_data_description,
            "supports_data_subject_requests": privacy.supports_data_subject_requests,
            "gdpr_compliant": privacy.gdpr_compliant,
            "data_returned_after_termination": privacy.data_returned_after_termination,
            "data_physical_location": privacy.data_physical_location
        })

    if hasattr(vendor_obj, 'business_maturity') and vendor_obj.business_maturity:
        maturity = vendor_obj.business_maturity[0]
        vendor_dict.update({
            "company_type": maturity.company_type,
            "total_funding": maturity.total_funding,
            "funding_round": maturity.funding_round,
            "has_enterprise_customers": maturity.has_enterprise_customers,
            "popularity_index": maturity.popularity_index,
            "revenue_estimate": maturity.revenue_estimate
        })

    return vendor_dict


def add_info_to_db(vendors, update_all_fields=True, model="sonar"):
    if not vendors:
        return {'statusCode': 400, 'body': json.dumps('No vendors to add.')}

    db.connect(reuse_if_open=True)
    updated_vendors = []
    inserted_vendors = []

    try:
        for vendor in vendors:
            vendor_obj, status = update_or_create_vendor(vendor, update_all_fields, model=model)
            if vendor_obj:
                if status == "created":
                    inserted_vendors.append(vendor_obj.vendor)
                else:
                    updated_vendors.append(vendor_obj.vendor)
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

    return {
        'statusCode': 200,
        'body': json.dumps({'Updated': updated_vendors, 'Inserted': inserted_vendors})
    }


def get_vendor_info_from_db(vendor_names):
    db.connect(reuse_if_open=True)
    results = []

    try:
        for vendor in vendor_names:
            normalized_vendor = basename(vendor).upper()
            vendor_obj = VendorProfile.select().where(
                VendorProfile.vendor ** f"%{normalized_vendor}%"
            ).first()

            if vendor_obj:
                results.append(get_complete_vendor_info(vendor_obj))
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

    return {'statusCode': 200, 'body': json.dumps(results, default=str)}


def get_all_vendors_from_db():
    db.connect(reuse_if_open=True)
    try:
        results = [
            {"id": str(v.id), "vendor": v.vendor, "logo": v.logo, "website_url": v.website_url}
            for v in VendorProfile.select(VendorProfile.id, VendorProfile.vendor,
                                         VendorProfile.logo, VendorProfile.website_url)
        ]
        return {'statusCode': 200, 'body': json.dumps(results, default=str)}
    except Exception as e:
        print(f"Error: {e}")
        return {'statusCode': 500, 'body': json.dumps('Error querying vendors')}
    finally:
        db.close()


def get_vendor_info_by_id_or_name(id=None, vendor_name=None):
    db.connect(reuse_if_open=True)
    try:
        if id:
            vendor_obj = VendorProfile.select().where(VendorProfile.id == id).first()
        elif vendor_name:
            normalized_vendor = basename(vendor_name).upper()
            vendor_obj = VendorProfile.select().where(VendorProfile.vendor == normalized_vendor).first()
        else:
            return {'statusCode': 400, 'body': json.dumps('ID or name required')}

        if vendor_obj:
            return {'statusCode': 200, 'body': json.dumps(get_complete_vendor_info(vendor_obj), default=str)}
        else:
            return {'statusCode': 404, 'body': json.dumps('Vendor not found')}
    except Exception as e:
        print(f"Error: {e}")
        return {'statusCode': 500, 'body': json.dumps('Internal server error')}
    finally:
        db.close()


def get_security_instances_by_vendor(id_or_name):
    db.connect(reuse_if_open=True)
    try:
        # Find vendor
        try:
            vendor_id = uuid.UUID(id_or_name)
            vendor_obj = VendorProfile.select().where(VendorProfile.id == vendor_id).first()
            vendor_name = vendor_obj.vendor if vendor_obj else None
        except Exception:
            vendor_name = basename(id_or_name).upper()
            vendor_obj = VendorProfile.select().where(VendorProfile.vendor == vendor_name).first()

        if not vendor_obj:
            return {'statusCode': 404, 'body': json.dumps('Vendor not found')}

        # Get RSS feeds (supporting both new foreign key and legacy vendor_name field)
        feeds_by_fk = list(RSSFeed.select().where(RSSFeed.vendor == vendor_obj))
        feeds_by_name = list(RSSFeed.select().where(RSSFeed.vendor_name == vendor_name))

        # Deduplicate by URL
        all_feeds = {feed.url: feed for feed in feeds_by_fk + feeds_by_name}.values()

        results = [
            {
                "id": str(feed.id),
                "title": feed.title,
                "vendor": vendor_name,
                "product": feed.product,
                "published": str(feed.published),
                "exploits": feed.exploits,
                "summary": feed.summary,
                "url": feed.url,
                "img": feed.img,
                "incident_type": feed.incident_type,
                "affected_service": feed.affected_service,
                "potentially_impacted_data": feed.potentially_impacted_data,
                "status": feed.status,
                "source": feed.source
            }
            for feed in all_feeds
        ]

        return {'statusCode': 200, 'body': json.dumps(results, default=str)}
    except Exception as e:
        print(f"Error: {e}")
        return {'statusCode': 500, 'body': json.dumps('Internal server error')}
    finally:
        db.close()


