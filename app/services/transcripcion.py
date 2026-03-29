"""Servicio de transcripción de audio usando Groq Whisper."""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

import httpx
from groq import AsyncGroq

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()
_client = AsyncGroq(api_key=settings.groq_api_key)

# Extensiones soportadas por Whisper
_SUPPORTED_EXTENSIONS = {".ogg", ".mp3", ".mp4", ".m4a", ".wav", ".webm", ".mpeg", ".mpga"}


async def descargar_audio(url: str) -> Path:
    """Descarga un archivo de audio desde *url* y lo guarda en un directorio temporal.

    Los archivos de media de Twilio requieren autenticación Basic con Account SID y Auth Token.
    Si las credenciales no están configuradas, hace la descarga sin autenticación.
    Retorna la ruta local del archivo descargado.
    """
    temp_dir = Path(settings.temp_audio_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)

    auth = None
    if settings.twilio_account_sid and settings.twilio_auth_token:
        auth = (settings.twilio_account_sid, settings.twilio_auth_token)

    async with httpx.AsyncClient(timeout=60, auth=auth) as client:
        response = await client.get(url)
        response.raise_for_status()

    # Determinar extensión a partir del Content-Type
    content_type = response.headers.get("content-type", "")
    ext = _content_type_to_ext(content_type)

    fd, tmp_path = tempfile.mkstemp(suffix=ext, dir=str(temp_dir))
    os.close(fd)
    Path(tmp_path).write_bytes(response.content)

    logger.info("Audio descargado: %s (%d bytes)", tmp_path, len(response.content))
    return Path(tmp_path)


async def transcribir_audio(audio_url: str) -> str:
    """Descarga el audio desde *audio_url* y devuelve la transcripción usando Groq Whisper.

    Limpia el archivo temporal después de la transcripción.
    """
    archivo = await descargar_audio(audio_url)
    try:
        with open(archivo, "rb") as f:
            transcripcion = await _client.audio.transcriptions.create(
                model="whisper-large-v3-turbo",
                file=f,
                language="es",
                response_format="text",
            )
        logger.info("Transcripción completada: %d caracteres", len(transcripcion))
        return transcripcion.strip()
    finally:
        archivo.unlink(missing_ok=True)


def _content_type_to_ext(content_type: str) -> str:
    """Mapea Content-Type a extensión de archivo."""
    mapping = {
        "audio/ogg": ".ogg",
        "audio/mpeg": ".mp3",
        "audio/mp4": ".m4a",
        "audio/wav": ".wav",
        "audio/webm": ".webm",
        "audio/x-m4a": ".m4a",
    }
    for ct, ext in mapping.items():
        if ct in content_type:
            return ext
    return ".ogg"  # Default para WhatsApp voice notes
