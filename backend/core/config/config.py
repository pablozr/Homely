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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @model_validator(mode="after")
    def require_production_secret(self):
        if self.ENVIRONMENT.lower() != "development" and (
            self.SECRET_KEY == DEFAULT_SECRET_KEY or len(self.SECRET_KEY) < 32
        ):
            raise ValueError("SECRET_KEY must have at least 32 characters outside development")

        return self


settings = Settings()

IS_DEVELOPMENT = settings.ENVIRONMENT.lower() == "development"
COOKIE_AUTH = "auth"
COOKIE_REFRESH = "refresh"
AUTH_COOKIE_MAX_AGE = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
REFRESH_COOKIE_MAX_AGE = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
ROLE_RANK_BY_NAME = {"BASIC": 1, "ADMIN": 2}
