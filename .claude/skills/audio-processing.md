# SKILL: Audio Processing con Groq Whisper

## Cuándo usar

Cuando trabajes con la transcripción de notas de voz de WhatsApp.

## Pipeline

```
URL audio → httpx download (límite 25 MB) → temp file → Groq Whisper API → texto → cleanup
```

## Código clave

```python
from groq import AsyncGroq

groq_client = AsyncGroq(api_key=settings.groq_api_key)

with open(archivo_local, "rb") as f:
    transcripcion = await groq_client.audio.transcriptions.create(
        model="whisper-large-v3-turbo",
        file=f,
        language="es",
        response_format="text",
    )
```

## Formatos soportados

`.mp3`, `.mp4`, `.mpeg`, `.mpga`, `.m4a`, `.wav`, `.webm`, `.ogg`

## WhatsApp voice notes

- Formato: OGG Opus (`audio/ogg; codecs=opus`)
- Límite de descarga: **25 MB** (rechazar antes de descargar completo)
- Whisper acepta OGG directamente, no necesita conversión.

## Limpieza

Siempre en bloque `finally`:

```python
try:
    # transcribir
finally:
    archivo.unlink(missing_ok=True)
```

## Código canónico

`shared/services/transcripcion.py` — los servicios de app/ y chatbot/ son shims.
