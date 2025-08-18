import peewee
import uuid
from peewee import *
from config import db

class BaseModel(Model):
    class Meta:
        database = db

class User(BaseModel):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    name = CharField(null=True)
    email = CharField(unique=True)

    class Meta:
        table_name = 'users'

class Account(BaseModel):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    name = CharField(unique=True)
    active = BooleanField(default=True)

    class Meta:
        table_name = 'accounts'

class AccountUser(BaseModel):
    account = ForeignKeyField(Account, backref='users')
    user = ForeignKeyField(User, backref='accounts')

    class Meta:
        table_name = 'account_users'
        primary_key = CompositeKey('account', 'user')

class Admin(BaseModel):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    email = CharField(unique=True)

    class Meta:
        table_name = 'admins'

class Vendor(BaseModel):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    name = CharField(unique=True)

    class Meta:
        table_name = 'vendors'

class VendorList(BaseModel):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    name = CharField()
    account = ForeignKeyField(Account, backref='vendor_lists')

    class Meta:
        table_name = 'vendor_lists'

class VendorListVendor(BaseModel):
    vendor_list = ForeignKeyField(VendorList, backref='vendors')
    vendor = ForeignKeyField(Vendor, backref='lists')

    class Meta:
        table_name = 'vendor_list_vendors'
        primary_key = CompositeKey('vendor_list', 'vendor')

class Subscriber(BaseModel):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    email = CharField(unique=True)
    verified = BooleanField(default=False)

    class Meta:
        table_name = 'subscribers'

class VendorListSubscriber(BaseModel):
    vendor_list = ForeignKeyField(VendorList, backref='subscribers')
    subscriber = ForeignKeyField(Subscriber, backref='lists')

    class Meta:
        table_name = 'vendor_list_subscribers'
        primary_key = CompositeKey('vendor_list', 'subscriber')