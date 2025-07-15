import peewee
from playhouse.postgres_ext import JSONField
from config import db
import uuid

class BaseModel(peewee.Model):
    class Meta:
        database = db

class VendorInfo(BaseModel):
    id = peewee.UUIDField(primary_key=True, default=uuid.uuid4)
    vendor = peewee.TextField(unique=True)
    s_and_c_cert = JSONField(null=True)
    bus_type = JSONField(null=True)
    data_collected = JSONField(null=True)
    legal_compliance = peewee.TextField(null=True)
    published_subprocessors = JSONField(null=True)
    privacy_policy_url = peewee.TextField(null=True)
    tos_url = peewee.TextField(null=True)
    date = peewee.TextField(null=True)
    logo = peewee.TextField(null=True)
    alias = JSONField(null=True)
    data = JSONField(null=True)
    security_rating = peewee.FloatField(null=True)
    risk_score = peewee.IntegerField(null=True)
    risk_categories = JSONField(null=True)
    compliance_certifications = JSONField(null=True)
    headquarters_location = peewee.TextField(null=True)
    contact_email = peewee.TextField(null=True)
    breach_history = JSONField(null=True)
    last_reviewed = peewee.DateTimeField(null=True)
    website_url = peewee.TextField(null=True)

    class Meta:
        table_name = 'vendor_info'

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