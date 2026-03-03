"""
SQLAlchemy User model – maps to the 'users' table in Supabase (PostgreSQL).
"""

from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id              = Column(String, primary_key=True)           # UUID string
    name            = Column(String, nullable=False)
    email           = Column(String, unique=True, nullable=False, index=True)
    username        = Column(String, unique=True, nullable=False, index=True)
    phone           = Column(String, nullable=True)
    avatar_url      = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)

    # Password-reset fields
    reset_code         = Column(String, nullable=True)           # 6-digit code
    reset_code_expires = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<User {self.email}>"
