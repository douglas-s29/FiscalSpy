from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://fiscalspy:password@db:5432/fiscalspy"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # Security
    SECRET_KEY: str = "change-this-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # AES
    AES_KEY: str = "change-this-aes-key-32-chars!!!!"

    # Asaas
    ASAAS_API_KEY: str = ""
    ASAAS_WEBHOOK_TOKEN: str = ""
    ASAAS_BASE_URL: str = "https://sandbox.asaas.com/api/v3"

    # App
    APP_NAME: str = "FiscalSpy"
    ENVIRONMENT: str = "development"
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:80"

    # Storage
    XML_STORAGE_PATH: str = "/app/storage/xml"
    CERT_STORAGE_PATH: str = "/app/storage/certificados"

    # Trial
    TRIAL_DAYS: int = 7

    def get_allowed_origins(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
