import uuid
from peewee import *
from playhouse.postgres_ext import JSONField
from config import db
from datetime import datetime

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

class VendorProfile(BaseModel):
    """Main vendor information table"""
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    vendor = TextField(unique=True)
    company_description = TextField(null=True)
    business_type = CharField(
        max_length=20, 
        choices=[('B2B', 'Business to Business'), ('B2C', 'Business to Consumer'), ('Government', 'Government')],
        null=True
    )
    founded_year = IntegerField(null=True)
    employee_count = IntegerField(null=True)
    industry = CharField(max_length=100, null=True)
    primary_product = TextField(null=True)
    customer_count_estimate = IntegerField(null=True)
    alias = JSONField(null=True)
    logo = TextField(null=True)
    website_url = TextField(null=True)
    privacy_policy_url = TextField(null=True)
    tos_url = TextField(null=True)
    headquarters_location = TextField(null=True)
    contact_email = TextField(null=True)
    data_collected = JSONField(null=True)
    security_rating = FloatField(null=True)
    risk_score = IntegerField(null=True)
    risk_categories = JSONField(null=True)
    breach_history = JSONField(null=True)
    date = TextField(null=True)
    last_reviewed = DateTimeField(null=True)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        table_name = 'vendor_profiles'

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

class RSSFeed(BaseModel):
    """RSS feed entries"""
    title = TextField()
    vendor = TextField()
    product = TextField()
    published = DateTimeField()
    exploits = TextField()
    summary = TextField()
    url = TextField(unique=True)
    img = TextField(null=True)
    incident_type = TextField(null=True)
    affected_service = TextField(null=True)
    potentially_impacted_data = TextField(null=True)
    status = TextField(null=True)
    source = TextField(null=True)

    class Meta:
        table_name = 'rss_feeds'

