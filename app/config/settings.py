"""
Centralized application configuration.

All configuration is sourced from environment variables so the exact same
codebase can be pointed at any environment (local, staging, production)
simply by swapping the .env file. Nothing here should ever contain a
hardcoded domain, secret, or connection string.
"""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Supabase -----------------------------------------------------
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_STORAGE_BUCKET: str = "pdfs"

    # --- Database -------------------------------------------------------
    DATABASE_URL: str

    # --- Public facing configuration ------------------------------------
    # Base URL used to build permanent QR redirect links. Must never be
    # hardcoded anywhere else in the codebase.
    PUBLIC_BASE_URL: str = "http://localhost:8000"

    # --- CORS -------------------------------------------------------------
    CORS_ORIGINS: str = "http://localhost:5173"

    # --- Third party services ------------------------------------------
    IP_GEOLOCATION_API_KEY: str = ""

    # --- Auth ----------------------------------------------------------------
    # Single-admin login gating the dashboard (viewing/creating/deleting
    # documents). The public /p/{uuid} and /download/{uuid} routes are never
    # gated by this — end recipients of a PDF never need to authenticate.
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = ""
    JWT_SECRET_KEY: str = ""
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # --- Trash -----------------------------------------------------------------
    TRASH_RETENTION_DAYS: int = 7

    # --- App ---------------------------------------------------------------
    APP_ENV: str = "local"
    APP_NAME: str = "PDF QR Management Service"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
