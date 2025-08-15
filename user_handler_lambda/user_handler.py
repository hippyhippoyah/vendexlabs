import json
from peewee import IntegrityError
from config import db
from models import User, Account, AccountUser

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

def add_users(account_id, users):
    db.connect(reuse_if_open=True)
    try:
        account = Account.get(Account.id == account_id)
        added = []
        exists = []

        for user_info in users:
            if isinstance(user_info, dict):
                email = user_info.get('email')
                name = user_info.get('name')
            else:
                email = user_info
                name = None

            if not email:
                continue

            user, created = User.get_or_create(email=email, defaults={'name': name})
            if not created and name and not user.name:
                user.name = name
                user.save()

            try:
                AccountUser.create(account=account, user=user)
                added.append(email)
            except IntegrityError:
                db.rollback()
                exists.append(email)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'users_added': added,
                'users_already_exist': exists
            })
        }

    except Account.DoesNotExist:
        return {
            'statusCode': 404,
            'body': json.dumps(f"Account with ID '{account_id}' not found")
        }
    except Exception as e:
        db.rollback()
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error adding users: {str(e)}")
        }
    finally:
        db.close()

def get_users(account_id):
    db.connect(reuse_if_open=True)
    try:
        account = Account.get(Account.id == account_id)
        query = User.select().join(AccountUser).where(AccountUser.account == account)
        users = [{'email': u.email, 'name': u.name} for u in query]
        return {
            'statusCode': 200,
            'body': json.dumps({'users': users})
        }
    except Account.DoesNotExist:
        return {
            'statusCode': 404,
            'body': json.dumps(f"Account with ID '{account_id}' not found")
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error fetching users: {str(e)}")
        }
    finally:
        db.close()

def delete_users(account_id, users):
    db.connect(reuse_if_open=True)
    deleted = []
    not_found = []

    try:
        account = Account.get(Account.id == account_id)

        for user_info in users:
            if isinstance(user_info, dict):
                email = user_info.get('email')
            else:
                email = user_info

            if not email:
                continue

            try:
                user = User.get(User.email == email)
                rows = AccountUser.delete().where(
                    (AccountUser.account == account) & (AccountUser.user == user)
                ).execute()
                if rows > 0:
                    deleted.append(email)
                else:
                    not_found.append(email)
            except User.DoesNotExist:
                not_found.append(email)

        return {
            'statusCode': 200,
            'body': json.dumps({'deleted': deleted, 'not_found': not_found})
        }

    except Account.DoesNotExist:
        return {
            'statusCode': 404,
            'body': json.dumps(f"Account with ID '{account_id}' not found")
        }
    finally:
        db.close()

def lambda_handler(event, context):
    try:
        method = event['requestContext']['http']['method'].upper()
        email = get_user_email(event)
        if not email:
            return {
                'statusCode': 401,
                'body': json.dumps("Unauthorized: No user email found")
            }

        body = event.get('body')
        if body:
            data = json.loads(body) if isinstance(body, str) else body
        else:
            data = event

        account_id = data.get('account_id')
        users = data.get('users', [])

        if not account_id:
            return {
                'statusCode': 400,
                'body': json.dumps("Missing required field: 'account_id'")
            }

        if method == 'POST':
            return add_users(account_id, users)
        elif method == 'GET':
            return get_users(account_id)
        elif method == 'DELETE':
            return delete_users(account_id, users)
        else:
            return {
                'statusCode': 405,
                'body': json.dumps('Method Not Allowed')
            }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f"Internal server error: {str(e)}")
        }
