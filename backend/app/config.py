from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://mailbox:mailbox_pass@localhost:5432/mailbox_db"
    REDIS_URL: str = "redis://localhost:6379/0"
    ENCRYPTION_KEY: str = ""
    TOKEN_CHECK_INTERVAL: int = 300
    TOKEN_CHECK_CONCURRENCY: int = 10
    ACCESS_TOKEN_CACHE_TTL: int = 3000

    model_config = {"env_file": ".env"}


settings = Settings()
