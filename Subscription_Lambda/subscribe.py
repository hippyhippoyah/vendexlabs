import os
import json
import psycopg2
from datetime import datetime
from cleanco import basename

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")

def lambda_handler(event, context):
    email = event['email']
    vendors = event['vendors']

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
        try:
            cursor.execute(
                "INSERT INTO vendors (vendor, emails, date_subscribed) VALUES (%s, %s, %s)",
                (basename(vendor), email, datetime.now())
            )
            subscribed.append(vendor)
        except psycopg2.IntegrityError:
            # If the email is already subscribed to the vendor, skip it
            conn.rollback()
            already_subscribed.append(vendor)
        except Exception as e:
            conn.rollback()
            return {
                'statusCode': 500,
                'body': json.dumps(f'Error subscribing to {vendor}: {str(e)}')
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
