import json
import uuid
from peewee import IntegrityError
from config import db
from models import Vendor, VendorList, VendorListVendor, Account, AccountUser, User

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
        # Convert account_id string to UUID
        account_uuid = uuid.UUID(account_id) if isinstance(account_id, str) else account_id
        account = Account.get(Account.id == account_uuid)
        user = User.get(User.email == email)
        return AccountUser.select().where(
            (AccountUser.account == account) & (AccountUser.user == user)
        ).exists()
    except (Account.DoesNotExist, User.DoesNotExist, ValueError):
        return False

def add_vendor_list(account_id, vendor_list_name):
    db.connect(reuse_if_open=True)
    try:
        # Convert account_id string to UUID
        account_uuid = uuid.UUID(account_id) if isinstance(account_id, str) else account_id
        account = Account.get(Account.id == account_uuid)
        VendorList.create(name=vendor_list_name, account=account)
        return {
            'statusCode': 200,
            'body': json.dumps(f"Vendor list '{vendor_list_name}' created for account ID '{account_id}'")
        }
    except IntegrityError:
        db.rollback()
        return {
            'statusCode': 409,
            'body': json.dumps("Vendor list already exists.")
        }
    except Account.DoesNotExist:
        return {
            'statusCode': 404,
            'body': json.dumps(f"Account with ID '{account_id}' not found")
        }
    except ValueError:
        return {
            'statusCode': 400,
            'body': json.dumps(f"Invalid UUID format for account ID: '{account_id}'")
        }
    except Exception as e:
        db.rollback()
        return {
            'statusCode': 500,
            'body': json.dumps(str(e))
        }
    finally:
        db.close()

def delete_vendor_list(account_id, vendor_list_id):
    db.connect(reuse_if_open=True)
    try:
        # Convert account_id string to UUID
        account_uuid = uuid.UUID(account_id) if isinstance(account_id, str) else account_id
        account = Account.get(Account.id == account_uuid)
        vendor_list_uuid = uuid.UUID(vendor_list_id) if isinstance(vendor_list_id, str) else vendor_list_id
        vendor_list = VendorList.get((VendorList.id == vendor_list_uuid) & (VendorList.account == account))
        vendor_list.delete_instance(recursive=True)
        return {
            'statusCode': 200,
            'body': json.dumps(f"Vendor list '{vendor_list_id}' deleted.")
        }
    except VendorList.DoesNotExist:
        return {
            'statusCode': 404,
            'body': json.dumps("Vendor list not found.")
        }
    except Account.DoesNotExist:
        return {
            'statusCode': 404,
            'body': json.dumps(f"Account with ID '{account_id}' not found")
        }
    except ValueError:
        return {
            'statusCode': 400,
            'body': json.dumps(f"Invalid UUID format for account ID: '{account_id}'")
        }
    finally:
        db.close()

def add_vendors_to_list(account_id, vendor_list_id, vendors):
    db.connect(reuse_if_open=True)
    try:
        # Convert account_id string to UUID
        account_uuid = uuid.UUID(account_id) if isinstance(account_id, str) else account_id
        account = Account.get(Account.id == account_uuid)
        vendor_list_uuid = uuid.UUID(vendor_list_id) if isinstance(vendor_list_id, str) else vendor_list_id
        vendor_list = VendorList.get((VendorList.id == vendor_list_uuid) & (VendorList.account == account))
        added = []
        for vendor_name in vendors:
            vendor = Vendor.get_or_create(name=vendor_name)[0]
            VendorListVendor.get_or_create(vendor_list=vendor_list, vendor=vendor)
            added.append(vendor_name)
        return {
            'statusCode': 200,
            'body': json.dumps({'vendors_added': added})
        }
    except VendorList.DoesNotExist:
        return {
            'statusCode': 404,
            'body': json.dumps("Vendor list not found.")
        }
    except Account.DoesNotExist:
        return {
            'statusCode': 404,
            'body': json.dumps(f"Account with ID '{account_id}' not found")
        }
    except ValueError:
        return {
            'statusCode': 400,
            'body': json.dumps(f"Invalid UUID format for account ID: '{account_id}'")
        }
    except Exception as e:
        db.rollback()
        return {
            'statusCode': 500,
            'body': json.dumps(str(e))
        }
    finally:
        db.close()

def remove_vendors_from_list(account_id, vendor_list_name, vendors):
    db.connect(reuse_if_open=True)
    try:
        # Convert account_id string to UUID
        account_uuid = uuid.UUID(account_id) if isinstance(account_id, str) else account_id
        account = Account.get(Account.id == account_uuid)
        vendor_list = VendorList.get((VendorList.name == vendor_list_name) & (VendorList.account == account))
        removed = []
        for vendor_name in vendors:
            try:
                vendor = Vendor.get(Vendor.name == vendor_name)
                deleted = VendorListVendor.delete().where(
                    (VendorListVendor.vendor_list == vendor_list) &
                    (VendorListVendor.vendor == vendor)
                ).execute()
                if deleted:
                    removed.append(vendor_name)
            except Vendor.DoesNotExist:
                # Vendor doesn't exist, so it's not in the list anyway
                continue
        return {
            'statusCode': 200,
            'body': json.dumps({'vendors_removed': removed})
        }
    except VendorList.DoesNotExist:
        return {
            'statusCode': 404,
            'body': json.dumps("Vendor list not found.")
        }
    except Account.DoesNotExist:
        return {
            'statusCode': 404,
            'body': json.dumps(f"Account with ID '{account_id}' not found")
        }
    except ValueError:
        return {
            'statusCode': 400,
            'body': json.dumps(f"Invalid UUID format for account ID: '{account_id}'")
        }
    except Exception as e:
        db.rollback()
        return {
            'statusCode': 500,
            'body': json.dumps(str(e))
        }
    finally:
        db.close()

def save_vendors_to_list(account_id, vendor_list_id, vendors):
    db.connect(reuse_if_open=True)
    try:
        # Convert account_id string to UUID
        account_uuid = uuid.UUID(account_id) if isinstance(account_id, str) else account_id
        account = Account.get(Account.id == account_uuid)
        vendor_list_uuid = uuid.UUID(vendor_list_id) if isinstance(vendor_list_id, str) else vendor_list_id
        vendor_list = VendorList.get((VendorList.id == vendor_list_uuid) & (VendorList.account == account))
        
        # Remove all existing vendors
        VendorListVendor.delete().where(VendorListVendor.vendor_list == vendor_list).execute()
        
        # Add new vendors
        added = []
        for vendor_name in vendors:
            vendor = Vendor.get_or_create(name=vendor_name)[0]
            VendorListVendor.create(vendor_list=vendor_list, vendor=vendor)
            added.append(vendor_name)
            
        return {
            'statusCode': 200,
            'body': json.dumps({'vendors_saved': added})
        }
    except Account.DoesNotExist:
        return {
            'statusCode': 404,
            'body': json.dumps("Account not found.")
        }
    except VendorList.DoesNotExist:
        return {
            'statusCode': 404,
            'body': json.dumps("Vendor list not found.")
        }
    except ValueError:
        return {
            'statusCode': 400,
            'body': json.dumps(f"Invalid UUID format for account ID: '{account_id}'")
        }
    except Exception as e:
        db.rollback()
        return {
            'statusCode': 500,
            'body': json.dumps(str(e))
        }
    finally:
        db.close()

def get_vendor_lists(account_id):
    db.connect(reuse_if_open=True)
    try:
        # Convert account_id string to UUID
        account_uuid = uuid.UUID(account_id) if isinstance(account_id, str) else account_id
        account = Account.get(Account.id == account_uuid)
        lists = VendorList.select().where(VendorList.account == account)
        result = []
        
        for vendor_list in lists:
            # Get all vendors for this list
            vendors = [
                v.name for v in Vendor.select().join(VendorListVendor).where(VendorListVendor.vendor_list == vendor_list)
            ]
            result.append({
                "id": str(vendor_list.id),
                "name": vendor_list.name,
                "vendors": vendors
            })
            
        return {
            'statusCode': 200,
            'body': json.dumps({'vendor_lists': result})
        }
    except Account.DoesNotExist:
        return {
            'statusCode': 404,
            'body': json.dumps("Account not found.")
        }
    except ValueError:
        return {
            'statusCode': 400,
            'body': json.dumps(f"Invalid UUID format for account ID: '{account_id}'")
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(str(e))
        }
    finally:
        db.close()

def get_vendors_from_list(account_id, vendor_list_id):
    db.connect(reuse_if_open=True)
    try:
        # Convert account_id string to UUID
        account_uuid = uuid.UUID(account_id) if isinstance(account_id, str) else account_id
        account = Account.get(Account.id == account_uuid)
        vendor_list_uuid = uuid.UUID(vendor_list_id) if isinstance(vendor_list_id, str) else vendor_list_id
        vendor_list = VendorList.get((VendorList.id == vendor_list_uuid) & (VendorList.account == account))
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
    except Account.DoesNotExist:
        return {
            'statusCode': 404,
            'body': json.dumps(f"Account with ID '{account_id}' not found")
        }
    except ValueError:
        return {
            'statusCode': 400,
            'body': json.dumps(f"Invalid UUID format for account ID: '{account_id}'")
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

    query_params = event.get('queryStringParameters') or {}
    account_id = query_params.get('account-id')
    vendor_list_name = query_params.get('vendor-list')
    operation = query_params.get('operation')  # New parameter for vendor operations

    vendors = data.get('vendors', [])

    if not account_id:
        return {'statusCode': 400, 'body': json.dumps("Missing 'account-id' field")}

    if not is_user_in_account(account_id, email):
        return {'statusCode': 403, 'body': json.dumps("Forbidden: Not authorized for this account")}

    if method == 'POST':
        if operation == 'save-vendors':
            # POST /vendor-lists?operation=save-vendors&vendor-list=mylist
            if not (vendor_list_name and vendors is not None):
                return {'statusCode': 400, 'body': json.dumps("Missing 'vendor-list' or 'vendors' field")}
            return save_vendors_to_list(account_id, vendor_list_name, vendors)
        else:
            # Default POST behavior - create vendor list
            if not vendor_list_name:
                return {'statusCode': 400, 'body': json.dumps("Missing 'vendor-list' field")}
            return add_vendor_list(account_id, vendor_list_name)

    elif method == 'DELETE':
        if not vendor_list_name:
            return {'statusCode': 400, 'body': json.dumps("Missing 'vendor-list' field")}
        return delete_vendor_list(account_id, vendor_list_name)

    elif method == 'GET':
        if vendor_list_name:
            return get_vendors_from_list(account_id, vendor_list_name)
        else:
            return get_vendor_lists(account_id)

    else:
        return {'statusCode': 405, 'body': json.dumps("Method Not Allowed")}
