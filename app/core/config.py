"""Configuración central de la aplicación."""

from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # OpenAI (opcional, reservado para futuro)
    openai_api_key: str = ""

    # Groq (LLM + Whisper)
    groq_api_key: str

    # Twilio / WhatsApp
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    whatsapp_verify_token: str = "dagma_verify_2024"

    # Database — Railway provee postgresql://, asyncpg necesita postgresql+asyncpg://
    database_url: str = "postgresql+asyncpg://dagma_user:dagma_pass@localhost:5432/emergencias_dagma"

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    temp_audio_dir: str = "./tmp/audio"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @field_validator("database_url", mode="before")
    @classmethod
    def _fix_database_url(cls, v: str) -> str:
        """Convierte postgresql:// o postgres:// a postgresql+asyncpg:// para asyncpg."""
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        if v.startswith("postgresql://") and "+asyncpg" not in v:
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
