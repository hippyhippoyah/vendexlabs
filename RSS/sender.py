import json
import boto3
from botocore.exceptions import ClientError

SES_REGION = 'us-east-1'
SENDER_EMAIL = 'do-not-reply@notification.vendexlabs.com'
LOGO_URL = "https://vendexlabstest.s3.us-east-1.amazonaws.com/logo.png"

def send_email_ses(recipients, entry):
    title, vendor, product, published, exploits, summary, url, img = entry
    print("Sending email to:", recipients)

    body = f"""
    <html>
        <head>
            <style>
                body {{ font-family: Calibri, sans-serif; background:#f9f9f9; padding:20px; color:#333; }}
                .container {{ background:#fff; padding:20px; border-radius:8px; box-shadow:0 2px 4px rgba(0,0,0,0.1); }}
                .logo-banner-container {{
                    background-color: #EFEEEC; /* Grey background on the sides */
                    padding: 0 20px; /* Padding on both sides */
                }}
                .logo-banner {{
                    background-image: url('{LOGO_URL}');
                    background-size: contain;
                    background-repeat: no-repeat;
                    background-position: center;
                    height: 100px; /* Adjust the height of the logo banner */
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
                    <p><strong>Vendor Product:</strong> {vendor} {product}</p>
                    <p><strong>Published Date:</strong> {published}</p>
                    <p><strong>Summary:</strong> {summary}</p>
                    <div class="image-container">
                        <img src="{img}" alt="Image" style="max-width:50%; border-radius:8px;">
                    </div>
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
                'Subject': {'Data': title},
                'Body': {'Html': {'Data': body}}
            }
        )
        print("Email sent! Message ID:", response['MessageId'])
    except ClientError as e:
        print("Error sending email:", e.response['Error']['Message'])