import json
import uuid
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

def is_user_in_account(account_id, email):
    try:
        # Convert account_id string to UUID
        account_uuid = uuid.UUID(account_id) if isinstance(account_id, str) else account_id
        account = Account.get(Account.id == account_uuid)
        user = User.get(User.email == email)
        return AccountUser.select().where(
            (AccountUser.account == account) & (AccountUser.user == user)
        ).exists()
    except (Account.DoesNotExist, User.DoesNotExist, ValueError):
        return False

def add_users(account_id, users):
    db.connect(reuse_if_open=True)
    try:
        # Convert account_id string to UUID
        account_uuid = uuid.UUID(account_id) if isinstance(account_id, str) else account_id
        account = Account.get(Account.id == account_uuid)
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
    except ValueError:
        return {
            'statusCode': 400,
            'body': json.dumps(f"Invalid UUID format for account ID: '{account_id}'")
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
        # Convert account_id string to UUID
        account_uuid = uuid.UUID(account_id) if isinstance(account_id, str) else account_id
        account = Account.get(Account.id == account_uuid)
        query = User.select().join(AccountUser).where(AccountUser.account == account)
        users = [{'email': u.email, 'name': u.name, 'id': str(u.id)} for u in query]
        return {
            'statusCode': 200,
            'body': json.dumps({'users': users})
        }
    except Account.DoesNotExist:
        return {
            'statusCode': 404,
            'body': json.dumps(f"Account with ID '{account_id}' not found")
        }
    except ValueError:
        return {
            'statusCode': 400,
            'body': json.dumps(f"Invalid UUID format for account ID: '{account_id}'")
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
        # Convert account_id string to UUID
        account_uuid = uuid.UUID(account_id) if isinstance(account_id, str) else account_id
        account = Account.get(Account.id == account_uuid)

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
    except ValueError:
        return {
            'statusCode': 400,
            'body': json.dumps(f"Invalid UUID format for account ID: '{account_id}'")
        }
    finally:
        db.close()

def get_user_accounts(email):
    db.connect(reuse_if_open=True)
    try:
        # Get all accounts that the user belongs to
        query = (Account
                .select()
                .join(AccountUser)
                .join(User)
                .where(User.email == email))
        
        accounts = [{'id': str(account.id), 'name': account.name, 'active': account.active} for account in query]
        return {
            'statusCode': 200,
            'body': json.dumps({'accounts': accounts})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error fetching user accounts: {str(e)}")
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
            data = {}

        query_params = event.get('queryStringParameters') or {}
        account_id = query_params.get('account-id')
        users = data.get('users', [])

        if method == 'GET' and not account_id:
            return get_user_accounts(email)

        if not account_id:
            return {
                'statusCode': 400,
                'body': json.dumps("Missing required field: 'account-id'")
            }
        if not is_user_in_account(account_id, email):
            return {
                'statusCode': 403,
                'body': json.dumps(f"Forbidden: User '{email}' does not have access to account '{account_id}'")
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
