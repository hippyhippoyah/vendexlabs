import os
import peewee

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")

# Split host and port if DB_HOST contains ':'
if DB_HOST and ':' in DB_HOST:
    DB_HOST, DB_PORT = DB_HOST.split(':', 1)

db = peewee.PostgresqlDatabase(
    DB_NAME,
    user=DB_USER,
    password=DB_PASS,
    host=DB_HOST,
    port=int(DB_PORT)
)
