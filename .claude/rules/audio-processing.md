---
paths:
  - "shared/services/transcripcion.py"
---

# Audio Processing — Reglas

- Descargar con `httpx.AsyncClient` (timeout=60s).
- Límite de tamaño: 25 MB — rechazar antes de descargar completo.
- Guardar en archivo temporal; limpiar con `unlink()` en bloque `finally`.
- Extensión basada en Content-Type del response.
- API Whisper: **Groq** `whisper-large-v3-turbo`, NO OpenAI. API key: `settings.groq_api_key`.
- Invocar con `await groq_client.audio.transcriptions.create(...)`.
- Idioma: `es`. Response format: `text`.
- Código canónico en `shared/services/transcripcion.py`.
