"""
Create app tables in Supabase PostgreSQL.
Run once: python create_tables.py
"""

from app.db import get_engine
from app.models.user import Base
from sqlalchemy import text

engine = get_engine()

print("Creating tables...")
Base.metadata.create_all(engine)

with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id VARCHAR(64) PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title VARCHAR(255) NOT NULL DEFAULT 'New Chat',
            preview TEXT NOT NULL DEFAULT '',
            tag VARCHAR(128) NOT NULL DEFAULT '',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id BIGSERIAL PRIMARY KEY,
            session_id VARCHAR(64) NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
            role VARCHAR(32) NOT NULL,
            content TEXT NOT NULL,
            message_type VARCHAR(32) NOT NULL DEFAULT 'text',
            chart_payload JSONB,
            image_path TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))
    conn.execute(text("ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS chart_payload JSONB"))
    conn.execute(text("ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS image_path TEXT"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated_at ON chat_sessions(updated_at DESC)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at ASC)"))

print("Done! 'users', 'chat_sessions', and 'chat_messages' are ready.")
