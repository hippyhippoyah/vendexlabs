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

    class Meta:
        table_name = 'rss_feeds'

class Subscription(BaseModel):
    vendor = peewee.TextField()
    emails = peewee.TextField()

    class Meta:
        table_name = 'subscriptions'
