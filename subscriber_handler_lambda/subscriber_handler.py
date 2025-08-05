import json
from peewee import IntegrityError
from config import db
from models import VendorList, Subscriber, VendorListSubscriber, Account, AccountUser, User

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
        account = Account.get(Account.id == account_id)
        user = User.get(User.email == email)
        return AccountUser.select().where(
            (AccountUser.account == account) & (AccountUser.user == user)
        ).exists()
    except (Account.DoesNotExist, User.DoesNotExist):
        return False

def add_subscriber(account_id, vendor_list_name, subscriber_email):
    db.connect(reuse_if_open=True)
    try:
        account = Account.get(Account.id == account_id)
        vendor_list = VendorList.get(
            (VendorList.name == vendor_list_name) & (VendorList.account == account)
        )
        subscriber, _ = Subscriber.get_or_create(email=subscriber_email)

        VendorListSubscriber.get_or_create(
            vendor_list=vendor_list,
            subscriber=subscriber
        )

        # Placeholder: Trigger verification email to subscriber
        print(f"Trigger verification email to {subscriber_email}")

        return {
            'statusCode': 200,
            'body': json.dumps(f"Subscriber '{subscriber_email}' added to '{vendor_list_name}'")
        }
    except (Account.DoesNotExist, VendorList.DoesNotExist):
        return {
            'statusCode': 404,
            'body': json.dumps("Account or vendor list not found.")
        }
    except IntegrityError:
        db.rollback()
        return {
            'statusCode': 409,
            'body': json.dumps("Subscriber already exists in this vendor list.")
        }
    finally:
        db.close()

def get_subscribers(account_id, vendor_list_name):
    db.connect(reuse_if_open=True)
    try:
        account = Account.get(Account.id == account_id)
        vendor_list = VendorList.get(
            (VendorList.name == vendor_list_name) & (VendorList.account == account)
        )

        subscribers = [
            {"email": s.email, "verified": s.verified}
            for s in Subscriber.select().join(VendorListSubscriber).where(
                VendorListSubscriber.vendor_list == vendor_list
            )
        ]
        return {
            'statusCode': 200,
            'body': json.dumps({"subscribers": subscribers})
        }
    except (Account.DoesNotExist, VendorList.DoesNotExist):
        return {
            'statusCode': 404,
            'body': json.dumps("Account or vendor list not found.")
        }
    finally:
        db.close()

def delete_subscriber(account_id, vendor_list_name, subscriber_email):
    db.connect(reuse_if_open=True)
    try:
        account = Account.get(Account.id == account_id)
        vendor_list = VendorList.get(
            (VendorList.name == vendor_list_name) & (VendorList.account == account)
        )
        subscriber = Subscriber.get(Subscriber.email == subscriber_email)

        deleted = VendorListSubscriber.delete().where(
            (VendorListSubscriber.vendor_list == vendor_list) &
            (VendorListSubscriber.subscriber == subscriber)
        ).execute()

        if deleted:
            return {
                'statusCode': 200,
                'body': json.dumps(f"Subscriber '{subscriber_email}' removed.")
            }
        else:
            return {
                'statusCode': 404,
                'body': json.dumps("Subscriber not found in the vendor list.")
            }
    except (Account.DoesNotExist, VendorList.DoesNotExist, Subscriber.DoesNotExist):
        return {
            'statusCode': 404,
            'body': json.dumps("Account, vendor list, or subscriber not found.")
        }
    finally:
        db.close()

def toggle_verified_status(account_id, subscriber_email):
    db.connect(reuse_if_open=True)
    try:
        subscriber = Subscriber.get(Subscriber.email == subscriber_email)
        subscriber.verified = not subscriber.verified
        subscriber.save()
        return {
            'statusCode': 200,
            'body': json.dumps({
                "email": subscriber.email,
                "verified": subscriber.verified
            })
        }
    except Subscriber.DoesNotExist:
        db.rollback()
        return {
            'statusCode': 404,
            'body': json.dumps("Subscriber not found.")
        }
    except Exception as e:
        db.rollback()
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error toggling verification status: {str(e)}")
        }
    finally:
        db.close()

def lambda_handler(event, context):
    method = event['requestContext']['http']['method'].upper()
    email = get_user_email(event)
    if not email:
        return {
            'statusCode': 401,
            'body': json.dumps("Unauthorized: No user email found")
        }

    body = event.get('body')
    if body:
        data = json.loads(body) if isinstance(body, str) else body
    else:
        data = event

    account_id = data.get('account_id')
    vendor_list_name = data.get('vendor_list')
    subscriber_email = data.get('subscriber_email')

    if not account_id or not vendor_list_name:
        return {
            'statusCode': 400,
            'body': json.dumps("Missing required fields: 'account_id' and 'vendor_list'")
        }

    if method in ['POST', 'DELETE', 'GET']:
        if not is_user_in_account(account_id, email):
            return {
                'statusCode': 403,
                'body': json.dumps("Forbidden: You do not have access to this account")
            }

    if method == 'POST':
        if not subscriber_email:
            return {
                'statusCode': 400,
                'body': json.dumps("Missing required field: 'subscriber_email'")
            }
        return add_subscriber(account_id, vendor_list_name, subscriber_email)

    elif method == 'GET':
        return get_subscribers(account_id, vendor_list_name)

    elif method == 'DELETE':
        if not subscriber_email:
            return {
                'statusCode': 400,
                'body': json.dumps("Missing required field: 'subscriber_email'")
            }
        return delete_subscriber(account_id, vendor_list_name, subscriber_email)

    elif method == 'PATCH':
        if not subscriber_email:
            return {
                'statusCode': 400,
                'body': json.dumps("Missing required field: 'subscriber_email'")
            }
        if email != subscriber_email:
            return {
                'statusCode': 403,
                'body': json.dumps("Forbidden: You can only toggle your own verification status.")
            }
        return toggle_verified_status(account_id, subscriber_email)

    else:
        return {
            'statusCode': 405,
            'body': json.dumps("Method Not Allowed")
        }
