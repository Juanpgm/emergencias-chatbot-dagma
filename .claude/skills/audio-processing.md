# SKILL: Audio Processing con OpenAI Whisper

## Cuándo usar

Cuando trabajes con la transcripción de notas de voz.

## Pipeline

```
URL audio → httpx download → temp file → Whisper API → texto → cleanup
```

## Código clave

```python
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=settings.openai_api_key)

with open(archivo_local, "rb") as f:
    transcripcion = await client.audio.transcriptions.create(
        model="whisper-1",
        file=f,
        language="es",      # Forzar español
        response_format="text",  # Solo texto plano
    )
```

## Formatos soportados por Whisper

`.mp3`, `.mp4`, `.mpeg`, `.mpga`, `.m4a`, `.wav`, `.webm`, `.ogg`

## WhatsApp voice notes

- Formato: OGG Opus (`audio/ogg; codecs=opus`)
- Tamaño máximo: 16 MB
- Whisper acepta OGG directamente, no necesita conversión.

## Limpieza

Siempre en bloque `finally`:

```python
try:
    # transcribir
finally:
    archivo.unlink(missing_ok=True)
```
