import peewee
from playhouse.postgres_ext import JSONField
from config import db
import uuid
from datetime import datetime

class BaseModel(peewee.Model):
    class Meta:
        database = db

class VendorProfile(BaseModel):
    """Main vendor information table"""
    id = peewee.UUIDField(primary_key=True, default=uuid.uuid4)
    vendor = peewee.TextField(unique=True)
    company_description = peewee.TextField(null=True)
    business_type = peewee.CharField(
        max_length=20, 
        choices=[('B2B', 'Business to Business'), ('B2C', 'Business to Consumer'), ('Government', 'Government')],
        null=True
    )
    founded_year = peewee.IntegerField(null=True)
    employee_count = peewee.IntegerField(null=True)
    industry = peewee.CharField(max_length=100, null=True)
    primary_product = peewee.TextField(null=True)
    customer_count_estimate = peewee.IntegerField(null=True)
    alias = JSONField(null=True)
    logo = peewee.TextField(null=True)
    website_url = peewee.TextField(null=True)
    privacy_policy_url = peewee.TextField(null=True)
    tos_url = peewee.TextField(null=True)
    headquarters_location = peewee.TextField(null=True)
    contact_email = peewee.TextField(null=True)
    data_collected = JSONField(null=True)
    security_rating = peewee.FloatField(null=True)
    risk_score = peewee.IntegerField(null=True)
    risk_categories = JSONField(null=True)
    breach_history = JSONField(null=True)
    date = peewee.TextField(null=True)  # Creation date
    last_reviewed = peewee.DateTimeField(null=True)
    created_at = peewee.DateTimeField(default=datetime.now)
    updated_at = peewee.DateTimeField(default=datetime.now)

    class Meta:
        table_name = 'vendor_profiles'

class VendorSecurity(BaseModel):
    """Security and compliance information for vendors"""
    id = peewee.UUIDField(primary_key=True, default=uuid.uuid4)
    vendor = peewee.ForeignKeyField(VendorProfile, backref='security_info', on_delete='CASCADE')
    compliance_certifications = JSONField(null=True)
    published_subprocessors = JSONField(null=True)
    created_at = peewee.DateTimeField(default=datetime.now)
    updated_at = peewee.DateTimeField(default=datetime.now)

    class Meta:
        table_name = 'vendor_security'

class PrivacyControls(BaseModel):
    """Privacy and data handling controls for vendors"""
    id = peewee.UUIDField(primary_key=True, default=uuid.uuid4)
    vendor = peewee.ForeignKeyField(VendorProfile, backref='privacy_controls', on_delete='CASCADE')
    shared_data_description = peewee.TextField(null=True)
    ml_training_data_description = peewee.TextField(null=True)
    supports_data_subject_requests = peewee.BooleanField(null=True)
    gdpr_compliant = peewee.BooleanField(null=True)
    data_returned_after_termination = peewee.BooleanField(null=True)
    data_physical_location = peewee.TextField(null=True)
    created_at = peewee.DateTimeField(default=datetime.now)
    updated_at = peewee.DateTimeField(default=datetime.now)

    class Meta:
        table_name = 'privacy_controls'

class BusinessMaturity(BaseModel):
    """Business maturity and market information for vendors"""
    id = peewee.UUIDField(primary_key=True, default=uuid.uuid4)
    vendor = peewee.ForeignKeyField(VendorProfile, backref='business_maturity', on_delete='CASCADE')
    company_type = peewee.CharField(
        max_length=10, 
        choices=[('Private', 'Private'), ('Public', 'Public')],
        null=True
    )
    total_funding = peewee.DecimalField(max_digits=15, decimal_places=2, null=True)
    funding_round = peewee.CharField(max_length=50, null=True)
    has_enterprise_customers = peewee.BooleanField(null=True)
    popularity_index = peewee.IntegerField(null=True)
    revenue_estimate = peewee.DecimalField(max_digits=15, decimal_places=2, null=True)
    created_at = peewee.DateTimeField(default=datetime.now)
    updated_at = peewee.DateTimeField(default=datetime.now)

    class Meta:
        table_name = 'business_maturity'

class RSSFeed(BaseModel):
    """RSS feed entries - keeping existing structure but linking to new vendor table"""
    id = peewee.UUIDField(primary_key=True, default=uuid.uuid4)
    title = peewee.TextField()
    vendor = peewee.ForeignKeyField(VendorProfile, backref='rss_feeds', on_delete='CASCADE', null=True)
    vendor_name = peewee.TextField()  # Keep for backward compatibility during migration
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

# Legacy model for backward compatibility during migration
class VendorInfo(BaseModel):
    """Legacy vendor info table - keep for migration purposes"""
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
