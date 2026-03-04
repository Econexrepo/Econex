import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

_engine = None  # singleton engine


def get_engine():
    """
    Create ONE SQLAlchemy engine for the whole app (singleton).
    Keeps connections low to avoid Supabase pooler 'max clients reached'.
    """
    global _engine

    if _engine is not None:
        return _engine

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("Missing DATABASE_URL in .env")

    _engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=2,        # keep small for Supabase pooler
        max_overflow=0,     # never exceed pool_size
        pool_timeout=30,    # wait up to 30s for a connection
        pool_recycle=1800,  # recycle idle conns (helps with cloud DBs)
    )
    return _engine