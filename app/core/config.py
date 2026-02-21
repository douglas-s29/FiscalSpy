from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",   # ignora POSTGRES_USER, POSTGRES_PASSWORD, etc.
    )

    # ── App ──────────────────────────────────────────────
    app_name: str = "FiscalSpy"
    app_env: Literal["development", "production"] = "development"
    secret_key: str = "dev-secret-key-troque-em-producao"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30

    # ── Database ─────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://fiscalspy:fiscalspy123@db:5432/fiscalspy"
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # ── Redis ────────────────────────────────────────────
    redis_url: str = "redis://:redis123@redis:6379/0"
    redis_password: str = ""

    # ── SEFAZ ────────────────────────────────────────────
    sefaz_ambiente: Literal["homologacao", "producao"] = "homologacao"
    sefaz_cert_path: str = "/app/certs/empresa.pfx"
    sefaz_cert_password: str = ""
    sefaz_timeout: int = 30

    # ── Webhooks ─────────────────────────────────────────
    webhook_max_retries: int = 5
    webhook_retry_delays: str = "10,30,120,600,3600"

    # ── Email ────────────────────────────────────────────
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "noreply@fiscalspy.com.br"

    # ── Sentry ───────────────────────────────────────────
    sentry_dsn: str = ""

    # ── CORS ─────────────────────────────────────────────
    cors_origins: str = "http://localhost:3000"

    # ── Computed ─────────────────────────────────────────
    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def webhook_retry_delays_list(self) -> list[int]:
        return [int(d) for d in self.webhook_retry_delays.split(",")]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
