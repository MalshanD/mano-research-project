"""
Drop ALL tables from the database.
SQLAlchemy will recreate them automatically when the server restarts
(because main.py calls Base.metadata.create_all on startup).

Run from the mano_api/ directory:
    python migrate_add_password.py
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

# ── must import all models so SQLAlchemy knows every table ──────────────────
from db.base import Base
from model import *          # loads User, Question, Response, etc.
# ────────────────────────────────────────────────────────────────────────────

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in your .env file.")

engine = create_engine(DATABASE_URL)

print("⚠️  Dropping ALL tables ...")
Base.metadata.drop_all(bind=engine)
print("✅  All tables dropped.")

print("🔨  Recreating ALL tables with updated schema ...")
Base.metadata.create_all(bind=engine)
print("✅  All tables recreated successfully!")
print()
print("You can now restart uvicorn — the database is ready with the new schema.")
