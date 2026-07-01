from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings

_INSECURE_PLACEHOLDERS = {"change-me-in-production", "dagma_verify_2024"}


class Settings(BaseSettings):
    groq_api_key: str
    database_url: str = "postgresql+asyncpg://dagma_user:dagma_pass@localhost:5432/emergencias_dagma"
    app_env: str = "development"
    log_level: str = "INFO"
    redis_url: str = "redis://localhost:6379/0"
    whatsapp_verify_token: str = "dagma_verify_2024"
    meta_whatsapp_token: str = ""
    meta_whatsapp_phone_id: str = ""
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    jwt_secret_key: str = "change-me-in-production"
    admin_username: str = "admin"
    admin_password: str = "change-me-in-production"
    firebase_api_key: str = ""
    firebase_allowed_domains: str = "gmail.com,cali.gov.co"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @field_validator("database_url", mode="before")
    @classmethod
    def _fix_database_url(cls, v: str) -> str:
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgresql://") and "+asyncpg" not in v:
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    @model_validator(mode="after")
    def _reject_insecure_defaults_in_production(self) -> "Settings":
        if self.app_env == "development":
            return self
        insecure = []
        if self.jwt_secret_key in _INSECURE_PLACEHOLDERS:
            insecure.append("JWT_SECRET_KEY")
        if self.admin_password in _INSECURE_PLACEHOLDERS:
            insecure.append("ADMIN_PASSWORD")
        if self.whatsapp_verify_token in _INSECURE_PLACEHOLDERS:
            insecure.append("WHATSAPP_VERIFY_TOKEN")
        if insecure:
            raise ValueError(
                f"Valores inseguros detectados en entorno '{self.app_env}': "
                f"{', '.join(insecure)}. Configura estas variables en .env."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
