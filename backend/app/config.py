from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()


class Settings(BaseSettings):
    SECRET_KEY: str = "econex-dev-secret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    FRONTEND_ORIGIN: str = "http://localhost:5173"
    openai_api_key: str
    some_other_setting: str = "default"


    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
