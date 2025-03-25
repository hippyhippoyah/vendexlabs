import os
import json
import psycopg2
from datetime import datetime

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
    cursor = conn.cursor()

    for vendor in vendors:
        cursor.execute(
            "INSERT INTO vendors (vendor, emails, date_subscribed) VALUES (%s, %s, %s)",
            (vendor, email, datetime.now())
        )

    conn.commit()
    cursor.close()
    conn.close()

    return {
        'statusCode': 200,
        'body': json.dumps('Subscription successful')
    }
