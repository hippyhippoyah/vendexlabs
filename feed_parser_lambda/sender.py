import json
import boto3
from botocore.exceptions import ClientError
import logging

SES_REGION = 'us-east-1'
SENDER_EMAIL = 'do-not-reply@notification.vendexlabs.com'
LOGO_URL = "https://vendexlabstest.s3.us-east-1.amazonaws.com/logo.png"

def send_email_ses(recipients, entry):

    title, vendor, product, published, exploits, summary, url, img, incident_type, affected_service, potentially_impacted_data, status, source = entry
    logging.info(f"Sending email to: {recipients}")

    image_html = ""
    if img:
        image_html = f'''
        <div class="image-container">
            <img src="{img}" alt="Image" style="max-width:50%; border-radius:8px;">
        </div>
        '''

    subject = f"{source}: {title}" if source else title

    body = f"""
    <html>
        <head>
            <style>
                body {{ font-family: Calibri, sans-serif; background:#f9f9f9; padding:20px; color:#333; }}
                .container {{ background:#fff; padding:20px; border-radius:8px; box-shadow:0 2px 4px rgba(0,0,0,0.1); }}
                .logo-banner-container {{
                    background-color: #EFEEEC;
                    padding: 0 20px;
                }}
                .logo-banner {{
                    background-image: url('{LOGO_URL}');
                    background-size: contain;
                    background-repeat: no-repeat;
                    background-position: center;
                    height: 100px;
                    width: 100%;
                }}
                .content {{ padding: 20px; }}
                .footer {{ margin-top:20px; font-size:12px; color:#777; text-align: center; }}
                .image-container {{
                    text-align: center;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="logo-banner-container">
                    <div class="logo-banner"></div>
                </div>
                <div class="content">
                    <p><em>Notification from VendexLabs</em></p>
                    <p><strong>Source:</strong> {source}</p>
                    <p><strong>Vendor Product:</strong> {vendor} {product}</p>
                    <p><strong>Published Date:</strong> {published}</p>
                    <p><strong>Incident Type:</strong> {incident_type}</p>
                    <p><strong>Affected Service:</strong> {affected_service}</p>
                    <p><strong>Potentially Impacted Data:</strong> {potentially_impacted_data}</p>
                    <p><strong>Status:</strong> {status}</p>
                    <p><strong>Summary:</strong> {summary}</p>
                    {image_html}
                    <p>Reference URL: <a href="{url}">{url}</a></p>
                    <p class="footer">Contact: info@vendexlabs.com</p>
                    <p class="footer"> Copyright 2025 VendexLabs.  All rights reserved. </p>
                </div>
            </div>
        </body>
    </html>
    """

    try:
        ses = boto3.client('ses', region_name=SES_REGION)
        response = ses.send_email(
            Source=SENDER_EMAIL,
            Destination={'ToAddresses': recipients},
            Message={
                'Subject': {'Data': subject},
                'Body': {'Html': {'Data': body}}
            }
        )
        logging.info(f"Email sent! Message ID: {response['MessageId']}")
    except ClientError as e:
        logging.error(f"Error sending email: {e.response['Error']['Message']}")