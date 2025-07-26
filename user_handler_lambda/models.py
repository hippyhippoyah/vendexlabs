import peewee
from config import db

class BaseModel(peewee.Model):
    class Meta:
        database = db

class User(BaseModel):
    name = peewee.TextField(null=True)
    email = peewee.TextField(unique=True)

    class Meta:
        table_name = 'users'

class Account(BaseModel):
    name = peewee.TextField(unique=True)
    active = peewee.BooleanField(default=True)

    class Meta:
        table_name = 'accounts'

class AccountUser(BaseModel):
    account = peewee.ForeignKeyField(Account, backref='users')
    user = peewee.ForeignKeyField(User, backref='accounts')

    class Meta:
        table_name = 'account_users'
        primary_key = peewee.CompositeKey('account', 'user')
