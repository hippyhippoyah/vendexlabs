from peewee import *
from config import db

class BaseModel(Model):
    class Meta:
        database = db

class Account(BaseModel):
    name = TextField(unique=True)
    active = BooleanField(default=True)

class User(BaseModel):
    email = TextField(unique=True)
    name = TextField(null=True)

class AccountUser(BaseModel):
    account = ForeignKeyField(Account, backref="users")
    user = ForeignKeyField(User, backref="accounts")

class Vendor(BaseModel):
    name = TextField(unique=True)

class VendorList(BaseModel):
    name = TextField()
    account = ForeignKeyField(Account, backref="vendor_lists")

class VendorListVendor(BaseModel):
    vendor_list = ForeignKeyField(VendorList, backref="vendors")
    vendor = ForeignKeyField(Vendor, backref="lists")

    class Meta:
        primary_key = CompositeKey('vendor_list', 'vendor')
