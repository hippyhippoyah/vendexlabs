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

class VendorList(BaseModel):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    name = TextField()
    account = ForeignKeyField(Account, backref='vendor_lists', null=True)
    user = ForeignKeyField(User, backref='personal_vendor_lists', null=True)

    class Meta:
        table_name = 'vendor_lists'

