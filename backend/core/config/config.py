from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_SECRET_KEY = "development-only-secret-key-change-me"


class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Backend"
    API_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    API_PORT: int = 8000

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_NAME: str = "app"

    SECRET_KEY: str = DEFAULT_SECRET_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_FROM_EMAIL: str = "no-reply@homely.local"
    SMTP_TIMEOUT_SECONDS: int = 10
    PUSH_ENABLED: bool = False

    MAGIC_LINK_EXPIRE_MINUTES: int = 15
    MAGIC_LINK_DEEP_LINK_BASE: str = "homely://auth"
    MAGIC_LINK_EMAIL_RATE_LIMIT: int = 3
    MAGIC_LINK_EMAIL_RATE_WINDOW_MINUTES: int = 15
    MAGIC_LINK_IP_RATE_LIMIT: int = 10
    MAGIC_LINK_IP_RATE_WINDOW_MINUTES: int = 60
    MAGIC_LINK_EXCHANGE_IP_RATE_LIMIT: int = 10
    MAGIC_LINK_EXCHANGE_IP_RATE_WINDOW_MINUTES: int = 15

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @model_validator(mode="after")
    def require_production_secret(self):
        if self.ENVIRONMENT.lower() != "development" and (
            self.SECRET_KEY == DEFAULT_SECRET_KEY or len(self.SECRET_KEY) < 32
        ):
            raise ValueError("SECRET_KEY must have at least 32 characters outside development")

        return self


settings = Settings()

ROLE_RANK_BY_NAME = {"BASIC": 1, "ADMIN": 2}
