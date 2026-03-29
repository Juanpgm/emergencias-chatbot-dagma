# SKILL: WhatsApp Integration via Twilio Webhook

## Cuándo usar

Cuando trabajes con el endpoint de WhatsApp o el procesamiento de mensajes.

## Estructura del payload de Twilio

Twilio envía el payload como `application/x-www-form-urlencoded`:

| Campo             | Tipo   | Descripción                                |
| ----------------- | ------ | ------------------------------------------ |
| MessageSid        | str    | ID único del mensaje                       |
| From              | str    | `whatsapp:+57300XXXXXXX`                   |
| To                | str    | `whatsapp:+1415XXXXXXX`                    |
| Body              | str?   | Texto del mensaje (vacío si es solo media) |
| NumMedia          | int    | Cantidad de archivos adjuntos              |
| MediaUrl0         | str?   | URL del primer adjunto                     |
| MediaContentType0 | str?   | MIME type del adjunto                      |
| Latitude          | float? | Lat si se envió ubicación                  |
| Longitude         | float? | Lon si se envió ubicación                  |

## Flujo de procesamiento

1. GET `/webhook/whatsapp` — verificación del webhook (challenge).
2. POST `/webhook/whatsapp` — mensaje entrante.
3. Detectar tipo: texto puro, nota de voz, ubicación.
4. Si audio → transcribir con Whisper.
5. Texto → extraer datos con LLM.
6. Guardar en DB.

## Seguridad

- Verificar `hub.verify_token` en GET.
- No exponer errores internos al usuario de WhatsApp.
- Limpiar archivos temporales de audio.
