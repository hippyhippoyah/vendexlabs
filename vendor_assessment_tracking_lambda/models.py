import uuid
from peewee import *
from config import db

class BaseModel(Model):
    class Meta:
        database = db

class Account(BaseModel):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    name = TextField(unique=True)
    active = BooleanField(default=True)

    class Meta:
        table_name = 'accounts'

class User(BaseModel):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
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
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    name = TextField(unique=True)

    class Meta:
        table_name = 'vendors'

class VendorList(BaseModel):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    name = TextField()
    account = ForeignKeyField(Account, backref='vendor_lists', null=True)
    user = ForeignKeyField(User, backref='personal_vendor_lists', null=True)

    class Meta:
        table_name = 'vendor_lists'

class VendorListVendor(BaseModel):
    vendor_list = ForeignKeyField(VendorList, backref="vendors")
    vendor = ForeignKeyField(Vendor, backref="lists")

    class Meta:
        table_name = 'vendor_list_vendors'
        primary_key = CompositeKey('vendor_list', 'vendor')

class VendorAssessment(BaseModel):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    vendor_list = ForeignKeyField(VendorList, backref='assessments')
    sponsor_business_org = TextField()
    sponsor_contact = TextField()
    compliance_approval_status = TextField()
    compliance_comment = TextField(null=True)
    compliance_contact = TextField()
    compliance_assessment_date = DateField(null=True)

    class Meta:
        table_name = 'vendor_assessments'
