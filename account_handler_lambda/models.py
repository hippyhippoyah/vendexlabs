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

class Admin(BaseModel):
    email = peewee.TextField(unique=True)

    class Meta:
        table_name = 'admins'

class AccountUser(BaseModel):
    account = peewee.ForeignKeyField(Account, backref='users')
    user = peewee.ForeignKeyField(User, backref='accounts')

    class Meta:
        table_name = 'account_users'
        primary_key = peewee.CompositeKey('account', 'user')

class Vendor(BaseModel):
    name = peewee.TextField()

    class Meta:
        table_name = 'vendors'

class VendorList(BaseModel):
    name = peewee.TextField()
    account = peewee.ForeignKeyField(Account, backref='vendor_lists')

    class Meta:
        table_name = 'vendor_lists'

class VendorListVendor(BaseModel):
    vendor_list = peewee.ForeignKeyField(VendorList, backref='vendors')
    vendor = peewee.ForeignKeyField(Vendor, backref='lists')

    class Meta:
        table_name = 'vendor_list_vendors'
        primary_key = peewee.CompositeKey('vendor_list', 'vendor')

class Subscriber(BaseModel):
    email = peewee.TextField(unique=True)
    verified = peewee.BooleanField(default=False)

    class Meta:
        table_name = 'subscribers'

class VendorListSubscriber(BaseModel):
    vendor_list = peewee.ForeignKeyField(VendorList, backref='subscribers')
    subscriber = peewee.ForeignKeyField(Subscriber, backref='lists')

    class Meta:
        table_name = 'vendor_list_subscribers'
        primary_key = peewee.CompositeKey('vendor_list', 'subscriber')