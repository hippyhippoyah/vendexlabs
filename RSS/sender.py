import json
import boto3
from botocore.exceptions import ClientError

SES_REGION = 'us-east-1'
SENDER_EMAIL = 'do-not-reply@notification.vendexlabs.com'
LOGO_URL = "https://i.imgur.com/7WiAVTV.png" # Change later

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
                    height: 150px; /* Adjust the height of the logo banner */
                    width: 100%;
                }}
                .content {{ padding: 20px; }}
                .footer {{ margin-top:20px; font-size:12px; color:#777; }}
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
                    <p><em>Notification from Vendex Labs</em></p>
                    <p><strong>Published:</strong> {published}</p>
                    <p><strong>Summary:</strong> {summary}</p>
                    <div class="image-container">
                        <img src="{img}" alt="Image" style="max-width:100%; border-radius:8px;">
                    </div>
                    <p><a href="{url}">Read more</a></p>
                    <p class="footer">This email was sent for {vendor} alert.</p>
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
