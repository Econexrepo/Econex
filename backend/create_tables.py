"""
Create the 'users' table in Supabase PostgreSQL.
Run once:  python create_tables.py
"""

from app.db import get_engine
from app.models.user import Base

engine = get_engine()

print("Creating tables...")
Base.metadata.create_all(engine)
print("Done! 'users' table created in your Supabase database.")
