import json
import logging
from peewee import IntegrityError
from config import db
from models import Account, User, AccountUser, VendorList, Admin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

def is_admin_email(email):
    return Admin.get_or_none(Admin.email == email) is not None

def add_account(account_name, users):
    db.connect(reuse_if_open=True)
    try:
        account, created = Account.get_or_create(name=account_name)
        created_users = []
        already_exists = []

        for user_email in users:
            user, _ = User.get_or_create(email=user_email)
            try:
                AccountUser.create(account=account, user=user)
                created_users.append(user_email)
            except IntegrityError:
                db.rollback()
                already_exists.append(user_email)

        master_list, master_created = VendorList.get_or_create(
            name='master-list', 
            account=account
        )

        return {
            'statusCode': 200,
            'body': json.dumps({
                'account_id': str(account.id),
                'account_name': account_name,
                'account_created': created,
                'users_added': created_users,
                'users_already_exist': already_exists,
                'vendor_list': 'master-list',
                'vendor_list_created': master_created
            })
        }
    except Exception as e:
        logger.error(f"Error creating account '{account_name}': {str(e)}")
        db.rollback()
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f"Error creating account '{account_name}': {str(e)}"})
        }
    finally:
        db.close()

def get_accounts():
    db.connect(reuse_if_open=True)
    try:
        query = Account.select()
        accounts = [{'id': str(a.id), 'name': a.name, 'active': a.active} for a in query]
        
        return {
            'statusCode': 200,
            'body': json.dumps({'accounts': accounts})
        }
    except Exception as e:
        logger.error(f"Error fetching accounts: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f"Error fetching accounts: {str(e)}"})
        }
    finally:
        db.close()

def delete_accounts(account_ids):
    db.connect(reuse_if_open=True)
    deleted = []
    not_found = []
    
    try:
        for acc_id in account_ids:
            try:
                account = Account.get_or_none(Account.id == acc_id)
                if not account:
                    not_found.append(str(acc_id))
                    continue

                AccountUser.delete().where(AccountUser.account == account).execute()
                VendorList.delete().where(VendorList.account == account).execute()
                Account.delete().where(Account.id == account.id).execute()
                
                deleted.append(str(acc_id))
                
            except Exception as e:
                logger.error(f"Error deleting account ID '{acc_id}': {str(e)}")
                db.rollback()
                return {
                    'statusCode': 500,
                    'body': json.dumps({'error': f"Error deleting account ID '{acc_id}': {str(e)}"})
                }
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'deleted': deleted,
                'not_found': not_found
            })
        }
    except Exception as e:
        logger.error(f"Error in delete_accounts: {str(e)}")
        db.rollback()
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f"Error deleting accounts: {str(e)}"})
        }
    finally:
        db.close()

def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")

    try:
        email = get_user_email(event)
        if not email:
            return {
                'statusCode': 401,
                'body': json.dumps({'error': 'Unauthorized: No user email found'})
            }

        if not is_admin_email(email):
            return {
                'statusCode': 403,
                'body': json.dumps({'error': 'Forbidden: Only admins can manage accounts'})
            }

        try:
            method = event['requestContext']['http']['method'].upper()
        except KeyError:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Bad Request: No HTTP method found'})
            }

        body = event.get('body')
        if body:
            try:
                data = json.loads(body) if isinstance(body, str) else body
            except json.JSONDecodeError:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': 'Bad Request: Invalid JSON in request body'})
                }
        else:
            data = event

        if method == 'POST':
            account_name = data.get('account')
            users = data.get('users', [])

            if not account_name:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': "Missing required field: 'account'"})
                }

            return add_account(account_name, users)

        elif method == 'GET':
            return get_accounts()

        elif method == 'DELETE':
            input_account_ids = []
            if 'account_id' in data:
                input_account_ids = [data['account_id']]
            elif 'account_ids' in data:
                input_account_ids = data['account_ids']
            else:
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': "Missing required field: 'account_id' or 'account_ids'"})
                }

            return delete_accounts(input_account_ids)

        else:
            return {
                'statusCode': 405,
                'body': json.dumps({'error': 'Method Not Allowed'})
            }

    except Exception as e:
        logger.error(f"Unexpected error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }
