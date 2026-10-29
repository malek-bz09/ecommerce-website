"""App settings, read from environment variables or the backend/.env file.

Every setting can be overridden by an environment variable with the same name in
capitals, e.g. DATABASE_URL=... uv run uvicorn app.main:app
"""

from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    # "development" shows nothing extra today, but lets later code behave differently in production
    environment: str = "development"

    # postgresql+psycopg:// tells SQLAlchemy to talk to PostgreSQL through the psycopg driver
    database_url: str = "postgresql+psycopg://shop:shop@localhost:5432/shop"

    # Websites allowed to call the API from a browser, comma-separated in .env
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    # Signs the login tokens. Anyone who knows it can forge an admin login, so it has
    # no default: the app refuses to start without one. SecretStr keeps it out of logs.
    jwt_secret_key: SecretStr = Field(min_length=32)
    access_token_minutes: int = 8 * 60

    # Requests allowed per client IP address, per minute
    login_rate_limit: int = 5
    order_rate_limit: int = 10

    # Where uploaded product photos are saved
    upload_dir: Path = BACKEND_DIR / "data" / "uploads"

    # Flat home-delivery fee in DZD. Keep in sync with DELIVERY_FEE in frontend/src/services/orders.js
    delivery_fee: Decimal = Decimal(600)

    # Times are stored in UTC; "orders per day" and date filters use the shop's local days
    shop_timezone: str = "Africa/Algiers"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value):
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Reads the settings once and reuses them afterwards."""
    return Settings()
