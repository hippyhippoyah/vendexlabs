from peewee import *
from config import db
import uuid

class BaseModel(Model):
    class Meta:
        database = db

class User(BaseModel):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    name = CharField(null=True)
    email = CharField(unique=True)

    class Meta:
        table_name = 'users'

class Vendor(BaseModel):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    name = CharField(unique=True)

    class Meta:
        table_name = 'vendors'

class VendorList(BaseModel):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    name = CharField()
    # account = ForeignKeyField(Account, backref='vendor_lists', null=True)
    user = ForeignKeyField(User, backref='personal_vendor_lists', null=True)

    class Meta:
        table_name = 'vendor_lists'

class VendorListVendor(BaseModel):
    vendor_list = ForeignKeyField(VendorList, backref='vendors')
    vendor = ForeignKeyField(Vendor, backref='lists')

    class Meta:
        table_name = 'vendor_list_vendors'
        primary_key = CompositeKey('vendor_list', 'vendor')