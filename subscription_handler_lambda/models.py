import peewee
from config import db

class BaseModel(peewee.Model):
    class Meta:
        database = db

class Subscription(BaseModel):
    vendor = peewee.TextField()
    emails = peewee.TextField()
    date_subscribed = peewee.DateTimeField(null=True)

    class Meta:
        table_name = 'subscriptions'
