import json
from peewee import IntegrityError
from config import db
from models import Account, User, AccountUser, VendorList, Admin

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

        master_list = VendorList.get_by_id(1)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'account_created': created,
                'users_added': created_users,
                'users_already_exist': already_exists,
                'vendor_list': 'master list'
            })
        }
    except Exception as e:
        db.rollback()
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error creating account '{account_name}': {str(e)}")
        }
    finally:
        db.close()

def get_accounts():
    db.connect(reuse_if_open=True)
    try:
        query = Account.select()
        accounts = [{'id': a.id, 'name': a.name, 'active': a.active} for a in query]
    except Exception as e:
        db.close()
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error fetching accounts: {str(e)}")
        }
    db.close()
    return {
        'statusCode': 200,
        'body': json.dumps({'accounts': accounts})
    }
def delete_accounts(account_names):
    db.connect(reuse_if_open=True)
    deleted = []
    not_found = []
    for name in account_names:
        try:
            account = Account.get_or_none(Account.name == name)
            if not account:
                not_found.append(name)
                continue

            AccountUser.delete().where(AccountUser.account == account).execute()
            VendorList.delete().where(VendorList.account == account).execute()
            Account.delete().where(Account.id == account.id).execute()
            deleted.append(name)
        except Exception as e:
            db.rollback()
            return {
                'statusCode': 500,
                'body': json.dumps(f"Error deleting account '{name}': {str(e)}")
            }
    db.close()
    return {
        'statusCode': 200,
        'body': json.dumps({
            'deleted': deleted,
            'not_found': not_found
        })
    }

def lambda_handler(event, context):
    print(event)

    email = get_user_email(event)
    if not email:
        return {
            'statusCode': 401,
            'body': json.dumps("Unauthorized: No user email found")
        }

    try:
        method = event['requestContext']['http']['method']
        method = method.upper()
    except KeyError:
        return {
            'statusCode': 400,
            'body': json.dumps('Bad Request: No HTTP method found')
        }

    body = event.get('body')
    if body:
        data = json.loads(body) if isinstance(body, str) else body
    else:
        data = event

    if method == 'POST':
        if not is_admin_email(email):
            return {
                'statusCode': 403,
                'body': json.dumps("Forbidden: Only admins can create accounts")
            }

        account_name = data.get('account')
        users = data.get('users', [])

        if not account_name:
            return {
                'statusCode': 400,
                'body': json.dumps("Missing required field: 'account'")
            }

        return add_account(account_name, users)

    elif method == 'GET':
        return get_accounts()

    elif method == 'DELETE':
        if not is_admin_email(email):
            return {
                'statusCode': 403,
                'body': json.dumps("Forbidden: Only admins can delete accounts")
            }

        # Unified handling of single or multiple account deletion
        input_accounts = []
        if 'account' in data:
            input_accounts = [data['account']]
        elif 'accounts' in data:
            input_accounts = data['accounts']
        else:
            return {
                'statusCode': 400,
                'body': json.dumps("Missing required field: 'account' or 'accounts'")
            }

        return delete_accounts(input_accounts)

    else:
        return {
            'statusCode': 405,
            'body': json.dumps('Method Not Allowed')
        }
