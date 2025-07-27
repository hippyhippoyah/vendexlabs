import json
from peewee import IntegrityError
from config import db
from models import Vendor, VendorList, VendorListVendor, Account, AccountUser, User

def get_user_email(event):
    claims = event['requestContext'].get('authorizer', {}).get('jwt', {}).get('claims', {})
    return claims.get('email')

def is_user_in_account(account_name, email):
    try:
        account = Account.get(Account.name == account_name)
        user = User.get(User.email == email)
        return AccountUser.select().where(
            (AccountUser.account == account) & (AccountUser.user == user)
        ).exists()
    except (Account.DoesNotExist, User.DoesNotExist):
        return False

def add_vendor_list(account_name, vendor_list_name):
    db.connect(reuse_if_open=True)
    try:
        account = Account.get(Account.name == account_name)
        VendorList.create(name=vendor_list_name, account=account)
        return {
            'statusCode': 200,
            'body': json.dumps(f"Vendor list '{vendor_list_name}' created for account '{account_name}'")
        }
    except IntegrityError:
        db.rollback()
        return {
            'statusCode': 409,
            'body': json.dumps("Vendor list already exists.")
        }
    except Exception as e:
        db.rollback()
        return {
            'statusCode': 500,
            'body': json.dumps(str(e))
        }
    finally:
        db.close()

def delete_vendor_list(account_name, vendor_list_name):
    db.connect(reuse_if_open=True)
    try:
        account = Account.get(Account.name == account_name)
        vendor_list = VendorList.get((VendorList.name == vendor_list_name) & (VendorList.account == account))
        vendor_list.delete_instance(recursive=True)
        return {
            'statusCode': 200,
            'body': json.dumps(f"Vendor list '{vendor_list_name}' deleted.")
        }
    except VendorList.DoesNotExist:
        return {
            'statusCode': 404,
            'body': json.dumps("Vendor list not found.")
        }
    finally:
        db.close()

def patch_vendors_in_list(account_name, vendor_list_name, vendors, action):
    db.connect(reuse_if_open=True)
    try:
        account = Account.get(Account.name == account_name)
        vendor_list = VendorList.get((VendorList.name == vendor_list_name) & (VendorList.account == account))
        processed = []
        for vendor_name in vendors:
            vendor = Vendor.get_or_create(name=vendor_name)[0]
            if action == "add":
                VendorListVendor.get_or_create(vendor_list=vendor_list, vendor=vendor)
                processed.append(vendor_name)
            elif action == "remove":
                deleted = VendorListVendor.delete().where(
                    (VendorListVendor.vendor_list == vendor_list) &
                    (VendorListVendor.vendor == vendor)
                ).execute()
                if deleted:
                    processed.append(vendor_name)
        return {
            'statusCode': 200,
            'body': json.dumps({f"vendors_{action}ed": processed})
        }
    except VendorList.DoesNotExist:
        return {
            'statusCode': 404,
            'body': json.dumps("Vendor list not found.")
        }
    finally:
        db.close()

def get_vendor_lists(account_name):
    db.connect(reuse_if_open=True)
    try:
        account = Account.get(Account.name == account_name)
        lists = VendorList.select().where(VendorList.account == account)
        result = [vl.name for vl in lists]
        return {
            'statusCode': 200,
            'body': json.dumps({'vendor_lists': result})
        }
    finally:
        db.close()

def get_vendors_from_list(account_name, vendor_list_name):
    db.connect(reuse_if_open=True)
    try:
        account = Account.get(Account.name == account_name)
        vendor_list = VendorList.get((VendorList.name == vendor_list_name) & (VendorList.account == account))
        vendors = [
            v.name for v in Vendor.select().join(VendorListVendor).where(VendorListVendor.vendor_list == vendor_list)
        ]
        return {
            'statusCode': 200,
            'body': json.dumps({'vendors': vendors})
        }
    except VendorList.DoesNotExist:
        return {
            'statusCode': 404,
            'body': json.dumps("Vendor list not found.")
        }
    finally:
        db.close()

def lambda_handler(event, context):
    method = event['requestContext']['http']['method'].upper()
    email = get_user_email(event)
    if not email:
        return {'statusCode': 401, 'body': json.dumps("Unauthorized")}

    body = event.get('body')
    data = json.loads(body) if isinstance(body, str) else body or event

    account_name = data.get('account')
    vendor_list_name = data.get('vendor_list')
    vendors = data.get('vendors', [])
    action = data.get('action')

    if not account_name:
        return {'statusCode': 400, 'body': json.dumps("Missing 'account' field")}

    if not is_user_in_account(account_name, email):
        return {'statusCode': 403, 'body': json.dumps("Forbidden: Not authorized for this account")}

    if method == 'POST':
        if not vendor_list_name:
            return {'statusCode': 400, 'body': json.dumps("Missing 'vendor_list' field")}
        return add_vendor_list(account_name, vendor_list_name)

    elif method == 'DELETE':
        if not vendor_list_name:
            return {'statusCode': 400, 'body': json.dumps("Missing 'vendor_list' field")}
        return delete_vendor_list(account_name, vendor_list_name)

    elif method == 'PATCH':
        if not (vendor_list_name and vendors and action in ['add', 'remove']):
            return {'statusCode': 400, 'body': json.dumps("Missing or invalid fields for PATCH")}
        return patch_vendors_in_list(account_name, vendor_list_name, vendors, action)

    elif method == 'GET':
        if vendor_list_name:
            return get_vendors_from_list(account_name, vendor_list_name)
        else:
            return get_vendor_lists(account_name)

    else:
        return {'statusCode': 405, 'body': json.dumps("Method Not Allowed")}
