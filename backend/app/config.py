"""
Econex application settings – loaded from .env automatically.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # JWT
    SECRET_KEY:                  str = "econex-dev-secret-change-in-production"
    ALGORITHM:                   str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # CORS
    FRONTEND_ORIGIN: str = "http://localhost:5173"

    # Hugging Face Router token – required; set in .env as HF_TOKEN
    # Get yours at: huggingface.co/settings/tokens
    hf_token: str = ""

    # SMTP / Email  ──────────────────────────────────────────────────────────
    # For Gmail: enable 2-FA, then create an App Password at
    # https://myaccount.google.com/apppasswords
    SMTP_HOST:     str = "smtp.gmail.com"
    SMTP_PORT:     int = 587
    SMTP_USER:     str = ""   # e.g. yourname@gmail.com
    SMTP_PASSWORD: str = ""   # Gmail App Password (16 chars, no spaces)

    class Config:
        env_file         = ".env"
        env_file_encoding = "utf-8"
        extra            = "ignore"   # silently ignore unknown env vars


settings = Settings()
