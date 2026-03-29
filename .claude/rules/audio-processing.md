---
paths:
  - "app/services/transcripcion.py"
---

# Audio Processing — Reglas

- Descargar con `httpx.AsyncClient` (timeout=60s).
- Guardar en directorio temporal configurado en `TEMP_AUDIO_DIR`.
- Usar `tempfile.mkstemp()` para nombres únicos; limpiar con `unlink()` en finally.
- Extensión basada en Content-Type del response.
- API Whisper: modelo `whisper-1`, idioma `es`, formato `text`.
- Operación asíncrona: `await client.audio.transcriptions.create()`.
