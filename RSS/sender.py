# Sender file using SES to send emails from lambda
# This is to be called by the main parser function
# Function takes in a list of emails and a message to send

import boto3
from botocore.exceptions import ClientError

def send_email_ses(recipients, entry):
    # Try to send the email.
    title, vendor, product, published, exploits, summary, url, img = entry
    try:
        ses_client = boto3.client('ses', region_name='us-east-1') 
        # Provide the contents of the email.
        print("Sending email to: " + str(recipients))
        body = f"""
            <html>
                <head>
                    <style>
                        body {{
                            font-family: Calibri, sans-serif;
                            line-height: 1.6;
                            color: #333;
                            background-color: #f9f9f9;
                            padding: 20px;
                        }}
                        p {{
                            margin: 10px 0;
                        }}
                        a {{
                            color: #1E90FF;
                            text-decoration: none;
                        }}
                        a:hover {{
                            text-decoration: underline;
                        }}
                        .email-container {{
                            background-color: #ffffff;
                            border: 1px solid #ddd;
                            border-radius: 8px;
                            padding: 20px;
                            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                        }}
                        .footer {{
                            margin-top: 20px;
                            font-size: 12px;
                            color: #777;
                        }}
                        .image-container {{
                            text-align: center;
                            margin: 20px 0;
                        }}
                        .image-container img {{
                            max-width: 100%;
                            height: auto;
                            border-radius: 8px;
                            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                        }}
                    </style>
                </head>
                <body>
                    <div class="email-container">
                        <h1><i>VENDEXLABS</i></h1>
                        <p><strong>Published:</strong> {published}</p>
                        <p><strong>Summary:</strong> {summary}</p>
                        <div class="image-container">
                            <img src="{img}" alt="VendexLabs Logo">
                        </div>
                        <p><a href="{url}">Read more</a></p>
                        <p class="footer">This email was sent for {vendor} alert.</p>
                    </div>
                </body>
            </html>
            """
        response = ses_client.send_email(
            Source='do-not-reply@notification.vendexlabs.com',
            Destination={
                'ToAddresses': recipients,
            },
            Message={
                'Subject': {
                    'Data': title,
                },
                'Body': {
                    'Html': {
                        'Data': body,
                    },
                },
            }
        )
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])