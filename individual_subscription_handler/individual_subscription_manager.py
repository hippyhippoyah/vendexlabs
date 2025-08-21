import json
from peewee import IntegrityError
from config import db
from models import User, VendorList, VendorListVendor, Vendor

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

def add_vendor_lists(email, vendors):
    db.connect(reuse_if_open=True)
    subscribed = []
    already_subscribed = []
    try:
        user, _ = User.get_or_create(email=email)
        for vendor_name in vendors:
            vendor, _ = Vendor.get_or_create(name=vendor_name)
            # Check if already exists
            exists = VendorListVendor.select().join(VendorList).where(
                (VendorList.user == user) & (VendorListVendor.vendor == vendor)
            ).exists()
            if exists:
                already_subscribed.append(vendor_name)
                continue
            # Create VendorList if not exists for user
            vendor_list, _ = VendorList.get_or_create(user=user, name=f"{user.email}_list")
            VendorListVendor.create(vendor_list=vendor_list, vendor=vendor)
            subscribed.append(vendor_name)
    except IntegrityError:
        db.rollback()
    except Exception as e:
        db.rollback()
        db.close()
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error subscribing: {str(e)}')
        }
    db.close()
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': f"Subscribed to: {', '.join(subscribed)}. Already subscribed to: {', '.join(already_subscribed)}."
        })
    }

def get_vendor_lists(email):
    db.connect(reuse_if_open=True)
    try:
        user = User.get(User.email == email)
        vendor_lists = VendorList.select().where(VendorList.user == user)
        vendors = []
        for vlist in vendor_lists:
            vlist_vendors = VendorListVendor.select().where(VendorListVendor.vendor_list == vlist)
            for v in vlist_vendors:
                vendors.append({"name": v.vendor.name})
    except User.DoesNotExist:
        db.close()
        return {
            'statusCode': 404,
            'body': json.dumps(f'User not found')
        }
    except Exception as e:
        db.close()
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error fetching vendor lists: {str(e)}')
        }
    db.close()
    return {
        'statusCode': 200,
        'body': json.dumps({
            'email': email,
            'vendors': vendors
        })
    }

def delete_vendor_lists(email, vendors):
    db.connect(reuse_if_open=True)
    deleted = []
    not_found = []
    try:
        user = User.get(User.email == email)
        vendor_lists = VendorList.select().where(VendorList.user == user)
        for vendor_name in vendors:
            vendor = Vendor.get_or_none(Vendor.name == vendor_name)
            if not vendor:
                not_found.append(vendor_name)
                continue
            found = False
            for vlist in vendor_lists:
                vlist_vendor = VendorListVendor.get_or_none(
                    (VendorListVendor.vendor_list == vlist) & (VendorListVendor.vendor == vendor)
                )
                if vlist_vendor:
                    vlist_vendor.delete_instance()
                    deleted.append(vendor_name)
                    found = True
                    break
            if not found:
                not_found.append(vendor_name)
    except User.DoesNotExist:
        db.close()
        return {
            'statusCode': 404,
            'body': json.dumps(f'User not found')
        }
    except Exception as e:
        db.close()
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error deleting vendor lists: {str(e)}')
        }
    db.close()
    return {
        'statusCode': 200,
        'body': json.dumps({
            'deleted': deleted,
            'not_found': not_found
        })
    }

def lambda_handler(event, context):
    print(event)
    user_email = get_user_email(event)
    if not user_email:
        return {
            'statusCode': 401,
            'body': json.dumps('Unauthorized: No claims found')
        }
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
        return add_vendor_lists(user_email, vendors)
    elif method == 'GET':
        return get_vendor_lists(user_email)
    elif method == 'DELETE':
        body = event.get('body')
        if body:
            data = json.loads(body) if isinstance(body, str) else body
        else:
            data = event
        vendors = data.get('vendors', [])
        return delete_vendor_lists(user_email, vendors)
    else:
        return {
            'statusCode': 405,
            'body': json.dumps('Method Not Allowed')
        }
