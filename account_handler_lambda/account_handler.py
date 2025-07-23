import json
from peewee import IntegrityError
from config import db
from models import Account, User, AccountUser, VendorList

def add_account(account_name, users):
    db.connect(reuse_if_open=True)
    try:
        account, created = Account.get_or_create(name=account_name)
        created_users = []
        already_exists = []

        for user_email in users:
            user, user_created = User.get_or_create(email=user_email)
            try:
                AccountUser.create(account=account, user=user)
                created_users.append(user_email)
            except IntegrityError:
                db.rollback()
                already_exists.append(user_email)

        VendorList.get_or_create(name='master list', account=account)

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

def delete_accounts(names):
    db.connect(reuse_if_open=True)
    deleted = []
    not_found = []
    for name in names:
        query = Account.delete().where(Account.name == name)
        rows_deleted = query.execute()
        if rows_deleted > 0:
            deleted.append(name)
        else:
            not_found.append(name)
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

    try:
        method = event['requestContext']['http']['method']
        method = method.upper()
    except KeyError:
        return {
            'statusCode': 400,
            'body': json.dumps('Bad Request: No HTTP method found')
        }

    if method == 'POST':
        body = event.get('body')
        if body:
            data = json.loads(body) if isinstance(body, str) else body
        else:
            data = event

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
        body = event.get('body')
        if body:
            data = json.loads(body) if isinstance(body, str) else body
        else:
            data = event
        names = data.get('names', [])
        return delete_accounts(names)

    else:
        return {
            'statusCode': 405,
            'body': json.dumps('Method Not Allowed')
        }