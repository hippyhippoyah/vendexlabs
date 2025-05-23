import peewee
from config import db

class BaseModel(peewee.Model):
    class Meta:
        database = db

class VendorInfo(BaseModel):
    vendor = peewee.TextField(unique=True)
    s_and_c_cert = peewee.TextField(null=True)
    bus_type = peewee.TextField(null=True)
    data_collected = peewee.TextField(null=True)
    legal_compliance = peewee.TextField(null=True)
    published_subprocessors = peewee.TextField(null=True)
    privacy_policy_url = peewee.TextField(null=True)
    tos_url = peewee.TextField(null=True)
    date = peewee.TextField(null=True)

    class Meta:
        table_name = 'vendor_info'
