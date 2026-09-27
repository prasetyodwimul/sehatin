from functools import lru_cache

from pydantic import Field, model_validator
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SEHATIN"
    environment: str = "development"
    cors_origins: str = "http://localhost:3000,http://localhost:3001"
    database_url: str = "postgresql+psycopg://sehatin:sehatin@localhost:5432/sehatin"

    # Operational persistence is optional. Personal Nutrition data from a public/guest
    # assessment requires a separate explicit opt-in and is OFF by default. Guided
    # Nutrition Program persistence remains explicit and authenticated.
    persistence_enabled: bool = False
    persist_anonymous_nutrition_personal_data: bool = False
    persist_health_claim_text: bool = False
    evidence_provider: str = "auto"  # demo | database | auto
    health_live_retrieval_enabled: bool = True
    health_live_max_results: int = Field(default=6, ge=1, le=8)
    health_fetch_timeout_seconds: float = Field(default=6.0, ge=1.0, le=20.0)
    health_url_max_bytes: int = Field(default=1_500_000, ge=100_000, le=5_000_000)
    health_checker_rate_limit_per_minute: int = Field(default=30, ge=1, le=300)
    health_checker_max_concurrent: int = Field(default=4, ge=1, le=20)
    blood_provider: str = "demo"  # demo | database | auto

    rate_limit_per_minute: int = Field(default=60, ge=1, le=10000)
    auth_rate_limit_per_minute: int = Field(default=10, ge=1, le=100)
    auth_session_minutes: int = Field(default=480, ge=15, le=10080)
    auth_pepper: str = "dev-only-change-me"
    auth_cookie_secure: bool = False
    max_request_bytes: int = Field(default=65536, ge=4096, le=5_000_000)
    # Development/testing only. Production always uses 24-hour nutrition day windows.
    nutrition_day_interval_seconds: int = Field(default=86400, ge=5, le=86400)
    # Optional for backward compatibility: when omitted in development, a
    # sub-24h NUTRITION_DAY_INTERVAL_SECONDS value activates the accelerated
    # interval schedule. Explicit "midnight" always wins.
    nutrition_day_schedule: Literal["midnight", "interval"] = "midnight"
    nutrition_timezone: str = "Asia/Jakarta"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def effective_nutrition_day_interval_seconds(self) -> int:
        if self.environment.lower() == "production":
            return 24 * 60 * 60
        return self.nutrition_day_interval_seconds
    @model_validator(mode="after")
    def validate_provider_names(self):
        if self.evidence_provider not in {"demo", "database", "auto"}:
            raise ValueError("EVIDENCE_PROVIDER harus demo, database, atau auto")
        if self.blood_provider not in {"demo", "database", "auto"}:
            raise ValueError("BLOOD_PROVIDER harus demo, database, atau auto")
        if self.environment.lower() == "production":
            if self.evidence_provider == "demo":
                raise ValueError("EVIDENCE_PROVIDER=demo tidak boleh digunakan pada environment production")
            if not self.auth_cookie_secure:
                raise ValueError("AUTH_COOKIE_SECURE harus true pada environment production")
            if not self.cors_origins_list or any(
                origin.strip() == "*" for origin in self.cors_origins_list
            ):
                raise ValueError(
                    "CORS_ORIGINS production harus berisi origin spesifik, bukan wildcard"
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()





