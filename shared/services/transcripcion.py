"""Servicio de transcripción de audio usando Groq Whisper."""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

import httpx
from groq import AsyncGroq

from shared.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()
_client = AsyncGroq(api_key=settings.groq_api_key)

# Extensiones soportadas por Whisper
_SUPPORTED_EXTENSIONS = {".ogg", ".mp3", ".mp4", ".m4a", ".wav", ".webm", ".mpeg", ".mpga"}

# Límite de tamaño de descarga de audio: 25 MB (límite de Groq Whisper)
_MAX_AUDIO_BYTES = 25 * 1024 * 1024


async def descargar_audio(url: str) -> Path:
    """Descarga un archivo de audio desde *url* y lo guarda en un directorio temporal.

    Aplica límite de tamaño (_MAX_AUDIO_BYTES) para evitar ataques DoS.
    Los archivos de media de Twilio requieren autenticación Basic con Account SID y Auth Token.
    Si las credenciales no están configuradas, hace la descarga sin autenticación.
    Retorna la ruta local del archivo descargado.
    """
    auth = None
    if settings.twilio_account_sid and settings.twilio_auth_token:
        auth = (settings.twilio_account_sid, settings.twilio_auth_token)

    async with httpx.AsyncClient(timeout=60, auth=auth, follow_redirects=True) as client:
        response = await client.get(url)
        if not response.is_success:
            logger.error(
                "Error descargando audio: HTTP %d — URL: %s — Body: %.200s",
                response.status_code, url, response.text,
            )
        response.raise_for_status()

    content = response.content
    if len(content) > _MAX_AUDIO_BYTES:
        raise ValueError(
            f"Audio excede el límite de {_MAX_AUDIO_BYTES // (1024 * 1024)} MB "
            f"({len(content)} bytes)"
        )

    content_type = response.headers.get("content-type", "")
    ext = _content_type_to_ext(content_type)

    fd, tmp_path = tempfile.mkstemp(suffix=ext)
    os.close(fd)
    Path(tmp_path).write_bytes(content)

    logger.info("Audio descargado: %d bytes", len(content))
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
