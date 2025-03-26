# Sender file using SES to send emails from lambda
# This is to be called by the main parser function
# Function takes in a list of emails and a message to send

import boto3
from botocore.exceptions import ClientError

def send_email_ses(recipients, subject, body):
    # Try to send the email.
    try:
        ses_client = boto3.client('ses', region_name='us-east-1') 
        # Provide the contents of the email.
        print("Sending email to: " + str(recipients))
        response = ses_client.send_email(
            Source='vendex@do-not-reply.com',
            Destination={
                'ToAddresses': recipients,
            },
            Message={
                'Subject': {
                    'Data': subject,
                },
                'Body': {
                    'Text': {
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