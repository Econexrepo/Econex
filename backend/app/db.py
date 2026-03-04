# app/db.py

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# -------------------------------------------------------------------
# ENV VARIABLES
# -------------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL")
WAREHOUSE_DATABASE_URL = os.getenv("WAREHOUSE_DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("Missing DATABASE_URL in .env")

if not WAREHOUSE_DATABASE_URL:
    raise RuntimeError("Missing WAREHOUSE_DATABASE_URL in .env")

# -------------------------------------------------------------------
# AUTH DATABASE (LOGIN / USERS)
# -------------------------------------------------------------------

auth_engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

AuthSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=auth_engine,
)

def get_auth_db():
    db = AuthSessionLocal()
    try:
        yield db
    finally:
        db.close()

# -------------------------------------------------------------------
# DATA WAREHOUSE DATABASE (ANALYTICS)
# -------------------------------------------------------------------

warehouse_engine = create_engine(
    WAREHOUSE_DATABASE_URL,
    pool_pre_ping=True,
)

WarehouseSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=warehouse_engine,
)

def get_warehouse_db():
    db = WarehouseSessionLocal()
    try:
        yield db
    finally:
        db.close()

# -------------------------------------------------------------------
# BACKWARD COMPATIBILITY
# (so existing auth code using get_engine() still works)
# -------------------------------------------------------------------

def get_engine():
    return auth_engine