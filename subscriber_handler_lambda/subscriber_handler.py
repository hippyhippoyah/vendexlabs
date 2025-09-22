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

def add_subscriber(account_id, vendor_list_id, subscriber_email):
    db.connect(reuse_if_open=True)
    try:
        account = Account.get(Account.id == account_id)
        vendor_list = VendorList.get(
            (VendorList.id == vendor_list_id) & (VendorList.account == account)
        )
        emails = subscriber_email if isinstance(subscriber_email, list) else [subscriber_email]
        added = []
        already_exists = []
        for email in emails:
            subscriber, _ = Subscriber.get_or_create(email=email)
            _, created = VendorListSubscriber.get_or_create(
                vendor_list=vendor_list,
                subscriber=subscriber
            )
            print(f"Trigger verification email to {email}")
            if created:
                added.append(email)
            else:
                already_exists.append(email)
        status = 200 if added else 409
        body = {
            "added": added,
            "already_exists": already_exists,
            "message": f"Added: {added}, Already exists: {already_exists}"
        }
        return {
            'statusCode': status,
            'body': json.dumps(body)
        }
    except (Account.DoesNotExist, VendorList.DoesNotExist):
        return {
            'statusCode': 404,
            'body': json.dumps("Account or vendor list not found.")
        }
    finally:
        db.close()

def get_subscribers(account_id, vendor_list_id):
    db.connect(reuse_if_open=True)
    try:
        account = Account.get(Account.id == account_id)
        vendor_list = VendorList.get(
            (VendorList.id == vendor_list_id) & (VendorList.account == account)
        )

        subscribers = [
            {"email": s.subscriber.email, "verified": s.subscriber.verified}
            for s in VendorListSubscriber.select().where(
                VendorListSubscriber.vendor_list == vendor_list
            ).join(Subscriber)
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

def delete_subscriber(account_id, vendor_list_id, subscriber_email):
    db.connect(reuse_if_open=True)
    try:
        account = Account.get(Account.id == account_id)
        vendor_list = VendorList.get(
            (VendorList.id == vendor_list_id) & (VendorList.account == account)
        )
        emails = subscriber_email if isinstance(subscriber_email, list) else [subscriber_email]
        removed = []
        not_found = []
        for email in emails:
            try:
                subscriber = Subscriber.get(Subscriber.email == email)
                deleted = VendorListSubscriber.delete().where(
                    (VendorListSubscriber.vendor_list == vendor_list) &
                    (VendorListSubscriber.subscriber == subscriber)
                ).execute()
                if deleted:
                    removed.append(email)
                else:
                    not_found.append(email)
            except Subscriber.DoesNotExist:
                not_found.append(email)
        status = 200 if removed else 404
        body = {
            "removed": removed,
            "not_found": not_found,
            "message": f"Removed: {removed}, Not found: {not_found}"
        }
        return {
            'statusCode': status,
            'body': json.dumps(body)
        }
    except (Account.DoesNotExist, VendorList.DoesNotExist):
        return {
            'statusCode': 404,
            'body': json.dumps("Account or vendor list not found.")
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

    query_params = event.get('queryStringParameters') or {}
    account_id = query_params.get('account-id')
    vendor_list_id = query_params.get('vendor-list')
    subscriber_email = data.get('subscriber-email')
    if isinstance(subscriber_email, str) and subscriber_email.startswith('[') and subscriber_email.endswith(']'):
        try:
            subscriber_email = json.loads(subscriber_email)
        except Exception:
            pass

    if not account_id or not vendor_list_id:
        return {
            'statusCode': 400,
            'body': json.dumps("Missing required fields: 'account-id', 'vendor-list-id'")
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
                'body': json.dumps("Missing required field: 'subscriber-email'")
            }
        return add_subscriber(account_id, vendor_list_id, subscriber_email)

    elif method == 'GET':
        return get_subscribers(account_id, vendor_list_id)

    elif method == 'DELETE':
        if not subscriber_email:
            return {
                'statusCode': 400,
                'body': json.dumps("Missing required field: 'subscriber-email'")
            }
        return delete_subscriber(account_id, vendor_list_id, subscriber_email)

    elif method == 'PATCH':
        if not subscriber_email:
            return {
                'statusCode': 400,
                'body': json.dumps("Missing required field: 'subscriber-email'")
            }
        if isinstance(subscriber_email, list):
            return {
                'statusCode': 400,
                'body': json.dumps("PATCH only supports a single subscriber-email.")
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
