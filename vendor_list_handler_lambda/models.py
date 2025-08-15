from peewee import *
from config import db

class BaseModel(Model):
    class Meta:
        database = db

class Account(BaseModel):
    name = TextField(unique=True)
    active = BooleanField(default=True)

    class Meta:
        table_name = 'accounts'

class User(BaseModel):
    email = TextField(unique=True)
    name = TextField(null=True)

    class Meta:
        table_name = 'users'

class AccountUser(BaseModel):
    account = ForeignKeyField(Account, backref="users")
    user = ForeignKeyField(User, backref="accounts")

    class Meta:
        table_name = 'account_users'
        primary_key = CompositeKey('account', 'user')

class Vendor(BaseModel):
    name = TextField(unique=True)

    class Meta:
        table_name = 'vendors'

class VendorList(BaseModel):
    name = TextField()
    account = ForeignKeyField(Account, backref="vendor_lists")

    class Meta:
        table_name = 'vendor_lists'

class VendorListVendor(BaseModel):
    vendor_list = ForeignKeyField(VendorList, backref="vendors")
    vendor = ForeignKeyField(Vendor, backref="lists")

    class Meta:
        table_name = 'vendor_list_vendors'
        primary_key = CompositeKey('vendor_list', 'vendor')
