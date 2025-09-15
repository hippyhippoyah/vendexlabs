import json
import uuid
from peewee import IntegrityError
from config import db
from models import VendorAssessment, VendorList, Account, AccountUser, User

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

def is_user_in_account(account_id, email):
    try:
        account_uuid = uuid.UUID(account_id) if isinstance(account_id, str) else account_id
        account = Account.get(Account.id == account_uuid)
        user = User.get(User.email == email)
        return AccountUser.select().where(
            (AccountUser.account == account) & (AccountUser.user == user)
        ).exists()
    except (Account.DoesNotExist, User.DoesNotExist, ValueError):
        return False

def add_vendor_assessment(account_id, vendor_list_id, assessment_data):
    db.connect(reuse_if_open=True)
    try:
        account_uuid = uuid.UUID(account_id) if isinstance(account_id, str) else account_id
        account = Account.get(Account.id == account_uuid)
        vendor_list = VendorList.get((VendorList.id == uuid.UUID(vendor_list_id)) & (VendorList.account == account))
        assessment = VendorAssessment.create(
            vendor_list=vendor_list,
            sponsor_business_org=assessment_data['sponsor_business_org'],
            sponsor_contact=assessment_data['sponsor_contact'],
            compliance_approval_status=assessment_data['compliance_approval_status'],
            compliance_comment=assessment_data.get('compliance_comment'),
            compliance_contact=assessment_data['compliance_contact'],
            compliance_assessment_date=assessment_data.get('compliance_assessment_date')
        )
        return {
            'statusCode': 200,
            'body': json.dumps({'id': str(assessment.id)})
        }
    except IntegrityError:
        db.rollback()
        return {
            'statusCode': 409,
            'body': json.dumps('Assessment already exists.')
        }
    except (Account.DoesNotExist, VendorList.DoesNotExist, ValueError):
        return {
            'statusCode': 404,
            'body': json.dumps('Account or Vendor List not found.')
        }
    except Exception as e:
        db.rollback()
        return {
            'statusCode': 500,
            'body': json.dumps(str(e))
        }
    finally:
        db.close()

def get_vendor_assessments(account_id, vendor_list_id):
    db.connect(reuse_if_open=True)
    try:
        account_uuid = uuid.UUID(account_id) if isinstance(account_id, str) else account_id
        account = Account.get(Account.id == account_uuid)
        vendor_list = VendorList.get((VendorList.id == uuid.UUID(vendor_list_id)) & (VendorList.account == account))
        assessments = VendorAssessment.select().where(VendorAssessment.vendor_list == vendor_list)
        result = []
        for a in assessments:
            result.append({
                'id': str(a.id),
                'sponsor_business_org': a.sponsor_business_org,
                'sponsor_contact': a.sponsor_contact,
                'compliance_approval_status': a.compliance_approval_status,
                'compliance_comment': a.compliance_comment,
                'compliance_contact': a.compliance_contact,
                'compliance_assessment_date': str(a.compliance_assessment_date) if a.compliance_assessment_date else None
            })
        return {
            'statusCode': 200,
            'body': json.dumps({'assessments': result})
        }
    except (Account.DoesNotExist, VendorList.DoesNotExist, ValueError):
        return {
            'statusCode': 404,
            'body': json.dumps('Account or Vendor List not found.')
        }
    finally:
        db.close()

def update_vendor_assessment(account_id, vendor_list_id, assessment_id, assessment_data):
    db.connect(reuse_if_open=True)
    try:
        account_uuid = uuid.UUID(account_id) if isinstance(account_id, str) else account_id
        account = Account.get(Account.id == account_uuid)
        vendor_list = VendorList.get((VendorList.id == uuid.UUID(vendor_list_id)) & (VendorList.account == account))
        assessment = VendorAssessment.get((VendorAssessment.id == uuid.UUID(assessment_id)) & (VendorAssessment.vendor_list == vendor_list))
        assessment.sponsor_business_org = assessment_data.get('sponsor_business_org', assessment.sponsor_business_org)
        assessment.sponsor_contact = assessment_data.get('sponsor_contact', assessment.sponsor_contact)
        assessment.compliance_approval_status = assessment_data.get('compliance_approval_status', assessment.compliance_approval_status)
        assessment.compliance_comment = assessment_data.get('compliance_comment', assessment.compliance_comment)
        assessment.compliance_contact = assessment_data.get('compliance_contact', assessment.compliance_contact)
        assessment.compliance_assessment_date = assessment_data.get('compliance_assessment_date', assessment.compliance_assessment_date)
        assessment.save()
        return {
            'statusCode': 200,
            'body': json.dumps('Assessment updated.')
        }
    except (Account.DoesNotExist, VendorList.DoesNotExist, VendorAssessment.DoesNotExist, ValueError):
        return {
            'statusCode': 404,
            'body': json.dumps('Account, Vendor List, or Assessment not found.')
        }
    except Exception as e:
        db.rollback()
        return {
            'statusCode': 500,
            'body': json.dumps(str(e))
        }
    finally:
        db.close()

def delete_vendor_assessment(account_id, vendor_list_id, assessment_id):
    db.connect(reuse_if_open=True)
    try:
        account_uuid = uuid.UUID(account_id) if isinstance(account_id, str) else account_id
        account = Account.get(Account.id == account_uuid)
        vendor_list = VendorList.get((VendorList.id == uuid.UUID(vendor_list_id)) & (VendorList.account == account))
        assessment = VendorAssessment.get((VendorAssessment.id == uuid.UUID(assessment_id)) & (VendorAssessment.vendor_list == vendor_list))
        assessment.delete_instance()
        return {
            'statusCode': 200,
            'body': json.dumps('Assessment deleted.')
        }
    except (Account.DoesNotExist, VendorList.DoesNotExist, VendorAssessment.DoesNotExist, ValueError):
        return {
            'statusCode': 404,
            'body': json.dumps('Account, Vendor List, or Assessment not found.')
        }
    finally:
        db.close()

# Lambda handler example

def lambda_handler(event, context):
    method = event['requestContext']['http']['method'].upper()
    email = get_user_email(event)
    if not email:
        return {'statusCode': 401, 'body': json.dumps('Unauthorized')}

    body = event.get('body')
    data = json.loads(body) if isinstance(body, str) else body or event
    query_params = event.get('queryStringParameters') or {}
    account_id = query_params.get('account-id')
    vendor_list_id = query_params.get('vendor-list-id')
    assessment_id = query_params.get('assessment-id')
    operation = query_params.get('operation')

    if not account_id or not vendor_list_id:
        return {'statusCode': 400, 'body': json.dumps("Missing 'account-id' or 'vendor-list-id' field")}

    if not is_user_in_account(account_id, email):
        return {'statusCode': 403, 'body': json.dumps('Forbidden: Not authorized for this account')}

    if method == 'POST':
        # Add assessment
        return add_vendor_assessment(account_id, vendor_list_id, data)
    elif method == 'GET':
        # Get assessments
        return get_vendor_assessments(account_id, vendor_list_id)
    elif method == 'PUT':
        # Update assessment
        if not assessment_id:
            return {'statusCode': 400, 'body': json.dumps("Missing 'assessment-id' field")}
        return update_vendor_assessment(account_id, vendor_list_id, assessment_id, data)
    elif method == 'DELETE':
        # Delete assessment
        if not assessment_id:
            return {'statusCode': 400, 'body': json.dumps("Missing 'assessment-id' field")}
        return delete_vendor_assessment(account_id, vendor_list_id, assessment_id)
    else:
        return {'statusCode': 405, 'body': json.dumps('Method Not Allowed')}
