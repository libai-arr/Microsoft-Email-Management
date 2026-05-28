import base64
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings


ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://mailbox:mailbox_pass@localhost:5432/mailbox_db"
    REDIS_URL: str = "redis://localhost:6379/0"
    ENCRYPTION_KEY: str = ""
    APP_SHARED_PASSWORD: str = ""
    APP_SHARED_PASSWORD_SESSION_TTL: int = 43200
    TOKEN_CHECK_INTERVAL: int = 300
    TOKEN_CHECK_CONCURRENCY: int = 10
    ACCESS_TOKEN_CACHE_TTL: int = 3000

    @field_validator("ENCRYPTION_KEY")
    @classmethod
    def validate_encryption_key(cls, v: str) -> str:
        if not v:
            raise ValueError("ENCRYPTION_KEY is required — generate with: python3 -c \"import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())\"")
        key_bytes = base64.b64decode(v)
        if len(key_bytes) != 32:
            raise ValueError("ENCRYPTION_KEY must be a 32-byte base64-encoded string")
        return v

    @field_validator("APP_SHARED_PASSWORD")
    @classmethod
    def validate_app_shared_password(cls, v: str) -> str:
        if not v:
            raise ValueError("APP_SHARED_PASSWORD is required")
        return v

    model_config = {"env_file": ENV_FILE, "extra": "ignore"}


settings = Settings()
