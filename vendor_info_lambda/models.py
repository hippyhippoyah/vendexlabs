import peewee
from playhouse.postgres_ext import JSONField
from config import db

class BaseModel(peewee.Model):
    class Meta:
        database = db

class VendorInfo(BaseModel):
    vendor = peewee.TextField(unique=True, primary_key=True)
    s_and_c_cert = JSONField(null=True)
    bus_type = JSONField(null=True)
    data_collected = peewee.TextField(null=True)
    legal_compliance = peewee.TextField(null=True)
    published_subprocessors = JSONField(null=True)
    privacy_policy_url = peewee.TextField(null=True)
    tos_url = peewee.TextField(null=True)
    date = peewee.TextField(null=True)
    logo = peewee.TextField(null=True)
    alias = JSONField(null=True)

    class Meta:
        table_name = 'vendor_info'
