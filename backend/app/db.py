import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_engine():
    if not DATABASE_URL:
        raise RuntimeError("Missing DATABASE_URL in .env")
    return create_engine(DATABASE_URL, pool_pre_ping=True)
