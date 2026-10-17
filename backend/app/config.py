from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DOMAIN: str = "localhost:8096"
    PUBLIC_BASE_URL: str = "http://localhost:8096"
    APP_PORT: int = 8096
    SECRET_KEY: str = "change-me-to-64-random-chars-minimum-0123456789abcdef0123456789ab"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    PAID_TOKEN_EXPIRE_MINUTES: int = 1440

    DATABASE_URL: str = "postgresql+psycopg2://links:links@postgres:5432/links"
    REDIS_URL: str = "redis://redis:6379/0"

    RATE_CREATE_PER_MIN: int = 30
    RATE_REDIRECT_PER_MIN: int = 120
    DEFAULT_SLUG_LEN: int = 7

    YOOKASSA_SHOP_ID: str = ""
    YOOKASSA_SECRET_KEY: str = ""
    YOOKASSA_RETURN_URL: str = ""
    YOOKASSA_MOCK: bool = True

    DATA_DIR: str = "/data"
    QR_DIR: str = "/data/qr"


settings = Settings()
