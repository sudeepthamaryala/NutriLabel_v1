from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Nutrition AI API"
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["*"]
    production_mode: bool = Field(default=False, alias="PRODUCTION_MODE")

    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    supabase_jwt_secret: str | None = Field(default=None, alias="SUPABASE_JWT_SECRET")
    supabase_jwt_audience: str = Field(default="authenticated", alias="SUPABASE_JWT_AUDIENCE")
    supabase_jwt_algorithm: str = Field(default="HS256", alias="SUPABASE_JWT_ALGORITHM")
    ocr_service_url: str | None = Field(default=None, alias="OCR_SERVICE_URL")
    inference_service_url: str | None = Field(default=None, alias="INFERENCE_SERVICE_URL")
    embedding_service_url: str | None = Field(default=None, alias="EMBEDDING_SERVICE_URL")
    health_check_external_services: bool = Field(default=False, alias="HEALTH_CHECK_EXTERNAL_SERVICES")
    external_service_timeout_seconds: float = Field(
        default=20.0,
        alias="EXTERNAL_SERVICE_TIMEOUT_SECONDS",
    )
    external_retry_attempts: int = Field(default=2, alias="EXTERNAL_RETRY_ATTEMPTS")
    max_question_chars: int = Field(default=1000, alias="MAX_QUESTION_CHARS")
    max_compare_images: int = Field(default=5, alias="MAX_COMPARE_IMAGES")
    rate_limit_requests: int = Field(default=20, alias="RATE_LIMIT_REQUESTS")
    rate_limit_window_seconds: int = Field(default=60, alias="RATE_LIMIT_WINDOW_SECONDS")
    redis_url: str | None = Field(default=None, alias="REDIS_URL")
    max_request_bytes: int = Field(default=10 * 1024 * 1024, alias="MAX_REQUEST_BYTES")
    storage_enabled: bool = Field(default=False, alias="STORAGE_ENABLED")
    supabase_url: str | None = Field(default=None, alias="SUPABASE_URL")
    supabase_anon_key: str | None = Field(default=None, alias="SUPABASE_ANON_KEY")
    supabase_service_role_key: str | None = Field(default=None, alias="SUPABASE_SERVICE_ROLE_KEY")
    supabase_storage_bucket: str | None = Field(default=None, alias="SUPABASE_STORAGE_BUCKET")
    storage_signed_url_ttl_seconds: int = Field(default=900, alias="STORAGE_SIGNED_URL_TTL_SECONDS")
    max_upload_bytes: int = Field(default=8 * 1024 * 1024, alias="MAX_UPLOAD_BYTES")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


def validate_startup_settings(settings: Settings) -> None:
    missing = []
    if not settings.database_url:
        missing.append("DATABASE_URL")
    if not settings.supabase_jwt_secret:
        missing.append("SUPABASE_JWT_SECRET")
    if settings.storage_enabled:
        if not settings.supabase_url:
            missing.append("SUPABASE_URL")
        if not settings.supabase_service_role_key:
            missing.append("SUPABASE_SERVICE_ROLE_KEY")
        if not settings.supabase_storage_bucket:
            missing.append("SUPABASE_STORAGE_BUCKET")
    if settings.production_mode and "*" in settings.cors_origins:
        missing.append("CORS_ORIGINS without wildcard in production")

    if missing:
        raise RuntimeError(f"Missing required configuration: {', '.join(missing)}")
