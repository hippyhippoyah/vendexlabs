import json
from datetime import datetime
from cleanco import basename
from peewee import IntegrityError
from config import db
from models import Subscription

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

def add_subscriptions(email, vendors):
    db.connect(reuse_if_open=True)
    subscribed = []
    already_subscribed = []
    for vendor in vendors:
        format_vendor = basename(vendor).upper()
        try:
            Subscription.create(
                vendor=format_vendor,
                emails=email,
                date_subscribed=datetime.now()
            )
            subscribed.append(format_vendor)
        except IntegrityError:
            db.rollback()
            already_subscribed.append(format_vendor)
        except Exception as e:
            db.rollback()
            db.close()
            return {
                'statusCode': 500,
                'body': json.dumps(f'Error subscribing to {format_vendor}: {str(e)}')
            }
    db.close()
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': f"Subscribed to: {', '.join(subscribed)}. Already subscribed to: {', '.join(already_subscribed)}."
        })
    }

def get_subscriptions(email):
    db.connect(reuse_if_open=True)
    try:
        query = Subscription.select().where(Subscription.emails == email)
        vendors = [
            {"name": row.vendor, "date": row.date_subscribed.isoformat() if row.date_subscribed else None}
            for row in query
        ]
    except Exception as e:
        db.close()
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error fetching subscriptions: {str(e)}')
        }
    db.close()
    return {
        'statusCode': 200,
        'body': json.dumps({
            'email': email,
            'vendors': vendors
        })
    }

def delete_subscriptions(email, vendors):
    db.connect(reuse_if_open=True)
    deleted = []
    not_found = []
    for vendor in vendors:
        format_vendor = basename(vendor).upper()
        query = Subscription.delete().where(
            (Subscription.vendor == format_vendor) & (Subscription.emails == email)
        )
        rows_deleted = query.execute()
        if rows_deleted > 0:
            deleted.append(format_vendor)
        else:
            not_found.append(format_vendor)
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
        return add_subscriptions(user_email, vendors)
    elif method == 'GET':
        return get_subscriptions(user_email)
    elif method == 'DELETE':
        body = event.get('body')
        if body:
            data = json.loads(body) if isinstance(body, str) else body
        else:
            data = event
        vendors = data.get('vendors', [])
        return delete_subscriptions(user_email, vendors)
    else:
        return {
            'statusCode': 405,
            'body': json.dumps('Method Not Allowed')
        }
