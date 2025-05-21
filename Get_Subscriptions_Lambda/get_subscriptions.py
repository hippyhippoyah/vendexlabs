import os
import json
import psycopg2
from datetime import datetime

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")

def lambda_handler(event, context):
    # Extract user email from claims
    claims = None
    authorizer = event['requestContext'].get('authorizer', {})
    if 'jwt' in authorizer and 'claims' in authorizer['jwt']:
        claims = authorizer['jwt']['claims']
    elif 'claims' in authorizer:
        claims = authorizer['claims']
    else:
        return {
            'statusCode': 401,
            'body': json.dumps('Unauthorized: No claims found')
        }
    user_email = claims.get('email')

    conn = psycopg2.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        dbname=DB_NAME
    )
    
    cursor = conn.cursor()
    try:
        # Get all vendors the user is subscribed to
        cursor.execute(
            "SELECT vendor, date_subscribed FROM vendors WHERE emails = %s",
            (user_email,)
        )
        subscriptions = [
            {"vendor": row[0], "date_subscribed": row[1].isoformat() if row[1] else None}
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
            'email': user_email,
            'subscriptions': subscriptions
        })
    }
