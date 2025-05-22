import os
import json
import psycopg2
from datetime import datetime
from cleanco import basename

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")

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
    conn = psycopg2.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        dbname=DB_NAME
    )
    subscribed = []
    already_subscribed = []
    cursor = conn.cursor()
    for vendor in vendors:
        format_vendor = basename(vendor).upper()
        try:
            cursor.execute(
                "INSERT INTO vendors (vendor, emails, date_subscribed) VALUES (%s, %s, %s)",
                (format_vendor, email, datetime.now())
            )
            subscribed.append(format_vendor)
        except psycopg2.IntegrityError:
            conn.rollback()
            already_subscribed.append(format_vendor)
        except Exception as e:
            conn.rollback()
            cursor.close()
            conn.close()
            return {
                'statusCode': 500,
                'body': json.dumps(f'Error subscribing to {format_vendor}: {str(e)}')
            }
    conn.commit()
    cursor.close()
    conn.close()
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': f"Subscribed to: {', '.join(subscribed)}. Already subscribed to: {', '.join(already_subscribed)}."
        })
    }

def get_subscriptions(email):
    conn = psycopg2.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        dbname=DB_NAME
    )
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT vendor, date_subscribed FROM vendors WHERE emails = %s",
            (email,)
        )
        vendors = [
            {"name": row[0], "date": row[1].isoformat() if row[1] else None}
            for row in cursor.fetchall()
        ]
    except Exception as e:
        cursor.close()
        conn.close()
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error fetching subscriptions: {str(e)}')
        }
    cursor.close()
    conn.close()
    return {
        'statusCode': 200,
        'body': json.dumps({
            'email': email,
            'vendors': vendors
        })
    }

def delete_subscriptions(email, vendors):
    conn = psycopg2.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        dbname=DB_NAME
    )
    cursor = conn.cursor()
    deleted = []
    not_found = []
    for vendor in vendors:
        format_vendor = basename(vendor).upper()
        cursor.execute(
            "DELETE FROM vendors WHERE vendor = %s AND emails = %s RETURNING vendor",
            (format_vendor, email)
        )
        if cursor.rowcount > 0:
            deleted.append(format_vendor)
        else:
            not_found.append(format_vendor)
    conn.commit()
    cursor.close()
    conn.close()
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
