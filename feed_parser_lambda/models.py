import os
import peewee

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")

db = peewee.PostgresqlDatabase(
    DB_NAME,
    user=DB_USER,
    password=DB_PASS,
    host=DB_HOST
)

class BaseModel(peewee.Model):
    class Meta:
        database = db

class RSSFeed(BaseModel):
    title = peewee.TextField()
    vendor = peewee.TextField()
    product = peewee.TextField()
    published = peewee.DateTimeField()
    exploits = peewee.TextField()
    summary = peewee.TextField()
    url = peewee.TextField(unique=True)
    img = peewee.TextField(null=True)
    incident_type = peewee.TextField(null=True)
    affected_service = peewee.TextField(null=True)
    potentially_impacted_data = peewee.TextField(null=True)
    status = peewee.TextField(null=True)
    source = peewee.TextField(null=True)

    class Meta:
        table_name = 'rss_feeds'


# --- Vendor List Models for Subscriber System ---
import uuid

class Account(BaseModel):
    id = peewee.UUIDField(primary_key=True, default=uuid.uuid4)
    name = peewee.TextField(unique=True)
    active = peewee.BooleanField(default=True)

    class Meta:
        table_name = 'accounts'


# Subscriber model for email notifications
class Subscriber(BaseModel):
    id = peewee.UUIDField(primary_key=True, default=uuid.uuid4)
    email = peewee.TextField(unique=True)
    verified = peewee.BooleanField(default=False)

    class Meta:
        table_name = 'subscribers'

class Vendor(BaseModel):
    id = peewee.UUIDField(primary_key=True, default=uuid.uuid4)
    name = peewee.TextField(unique=True)

    class Meta:
        table_name = 'vendors'

class VendorList(BaseModel):
    id = peewee.UUIDField(primary_key=True, default=uuid.uuid4)
    name = peewee.TextField()
    account = peewee.ForeignKeyField(Account, backref='vendor_lists', null=True)
    # user = peewee.ForeignKeyField(User, backref='personal_vendor_lists', null=True)  # Deprecated, use subscribers

    class Meta:
        table_name = 'vendor_lists'

# Link table for VendorList and Subscriber
class VendorListSubscriber(BaseModel):
    vendor_list = peewee.ForeignKeyField(VendorList, backref='subscribers')
    subscriber = peewee.ForeignKeyField(Subscriber, backref='lists')

    class Meta:
        table_name = 'vendor_list_subscribers'
        primary_key = peewee.CompositeKey('vendor_list', 'subscriber')

class VendorListVendor(BaseModel):
    vendor_list = peewee.ForeignKeyField(VendorList, backref="vendors")
    vendor = peewee.ForeignKeyField(Vendor, backref="lists")

    class Meta:
        table_name = 'vendor_list_vendors'
        primary_key = peewee.CompositeKey('vendor_list', 'vendor')
