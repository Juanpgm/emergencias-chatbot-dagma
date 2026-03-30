"""Router de webhook para recibir mensajes de WhatsApp (Twilio)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse

from app.core.config import get_settings
from app.core.database import get_db
from app.schemas.emergencia import WebhookResponse
from app.services.extraccion import extraer_datos_emergencia
from app.services.persistencia import guardar_reporte
from app.services.transcripcion import transcribir_audio

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/webhook", tags=["WhatsApp"])


def _twiml_response(mensaje: str) -> Response:
    """Construye una respuesta TwiML con el texto dado para enviar al usuario por WhatsApp."""
    resp = MessagingResponse()
    resp.message(mensaje)
    return Response(content=str(resp), media_type="application/xml")


# ── Validación de firma Twilio ─────────────────────────────────────────────────

async def _validar_firma_twilio(request: Request) -> None:
    """Verifica que la petición viene realmente de Twilio.

    Solo activa la validación en producción o cuando auth_token está configurado.
    En desarrollo sin auth_token configurado, omite la validación.
    """
    if not settings.twilio_auth_token:
        logger.debug("twilio_auth_token no configurado — omitiendo validación de firma")
        return

    validator = RequestValidator(settings.twilio_auth_token)
    signature = request.headers.get("X-Twilio-Signature", "")

    # Reconstruir URL con https:// usando X-Forwarded-Proto (Railway usa proxy inverso)
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    url = str(request.url).replace(f"{request.url.scheme}://", f"{proto}://", 1)

    form_data = await request.form()
    params = dict(form_data)

    if not validator.validate(url, params, signature):
        logger.warning("Firma Twilio inválida desde %s — url=%s", request.client.host, url)
        raise HTTPException(status_code=403, detail="Firma de Twilio inválida.")


# ── Verificación del webhook (GET) — Meta WhatsApp Business API ────────────────

@router.get("/whatsapp")
async def verificar_webhook(
    hub_mode: str | None = Query(None, alias="hub.mode"),
    hub_challenge: str | None = Query(None, alias="hub.challenge"),
    hub_verify_token: str | None = Query(None, alias="hub.verify_token"),
):
    """Verificación de webhook para Meta WhatsApp Business API."""
    if hub_verify_token == settings.whatsapp_verify_token:
        return int(hub_challenge) if hub_challenge else "OK"
    raise HTTPException(status_code=403, detail="Token de verificación inválido.")


# ── Recepción de mensajes (POST) — Twilio ─────────────────────────────────────

_MENSAJES_GRAVEDAD = {
    "alta": "⚠️ URGENTE",
    "media": "🔶 Atención requerida",
    "baja": "🔷 Registrado",
}

_MENSAJES_TIPO = {
    "arbol_caido": "🌳 Árbol caído",
    "rescate_animales_silvestres": "🦜 Rescate de animal silvestre",
    "tala_arboles": "🪓 Tala de árboles",
    "contaminacion_fuente_hidrica": "💧 Contaminación hídrica",
}


@router.post("/whatsapp")
async def recibir_mensaje_whatsapp(
    request: Request,
    From: str = Form(...),
    Body: str | None = Form(None),
    NumMedia: int = Form(0),
    MediaUrl0: str | None = Form(None),
    MediaContentType0: str | None = Form(None),
    Latitude: float | None = Form(None),
    Longitude: float | None = Form(None),
    MessageSid: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Recibe un mensaje de WhatsApp enviado por Twilio y lo procesa.

    Flujo:
    1. Valida firma Twilio (solo si auth_token está configurado).
    2. Si hay audio → transcribir con Groq Whisper.
    3. Enviar texto al LLM para extraer datos estructurados.
    4. Enriquecer con coordenadas GPS si se enviaron.
    5. Guardar en tabla maestra + tabla especializada por tipo.
    6. Responder al usuario con TwiML.
    """
    await _validar_firma_twilio(request)

    texto_para_analizar: str = ""
    texto_original: str = ""

    try:
        # ── 1. Procesar audio si existe ────────────────────────────────────
        if NumMedia > 0 and MediaUrl0 and _es_audio(MediaContentType0):
            logger.info("Procesando nota de voz de %s", From)
            texto_para_analizar = await transcribir_audio(MediaUrl0)
            texto_original = f"[AUDIO TRANSCRITO] {texto_para_analizar}"
        elif Body:
            texto_para_analizar = Body.strip()
            texto_original = Body.strip()
        else:
            return _twiml_response(
                "Hola 👋 Por favor envía un mensaje de texto o nota de voz "
                "describiendo la emergencia ambiental que deseas reportar."
            )

        # Agregar coordenadas al contexto si se enviaron
        if Latitude is not None and Longitude is not None:
            texto_para_analizar += (
                f"\n\n[Ubicación GPS proporcionada: lat={Latitude}, lon={Longitude}]"
            )

        # ── 2. Extraer datos con LLM ──────────────────────────────────────
        datos = await extraer_datos_emergencia(texto_para_analizar)

        # Sobrescribir coordenadas con las reales si fueron proporcionadas
        if Latitude is not None and Longitude is not None:
            datos.latitud = Latitude
            datos.longitud = Longitude

        # ── 3. Guardar en DB ──────────────────────────────────────────────
        reporte = await guardar_reporte(
            db=db,
            datos=datos,
            whatsapp_from=From,
            texto_original=texto_original,
        )

        logger.info("Reporte #%d creado para %s", reporte.id, From)

        # ── 4. Construir respuesta para el usuario ────────────────────────
        tipo_label = _MENSAJES_TIPO.get(datos.tipo_de_emergencia.value, datos.tipo_de_emergencia.value)
        gravedad_label = _MENSAJES_GRAVEDAD.get(datos.nivel_de_gravedad.value, datos.nivel_de_gravedad.value)
        ubicacion = datos.direccion_hechos or datos.ubicacion_inferida or "ubicación no especificada"

        respuesta = (
            f"✅ *Reporte #{reporte.id} registrado en DAGMA*\n\n"
            f"*Tipo:* {tipo_label}\n"
            f"*Gravedad:* {gravedad_label}\n"
            f"*Ubicación:* {ubicacion}\n\n"
            f"_{datos.descripcion_emergencia}_\n\n"
            f"Un equipo del DAGMA atenderá tu reporte. Gracias por cuidar el medio ambiente de Cali 🌿"
        )

        return _twiml_response(respuesta)

    except HTTPException:
        raise
    except Exception:
        logger.exception("Error procesando mensaje de %s", From)
        return _twiml_response(
            "Lo sentimos, ocurrió un error procesando tu reporte. "
            "Por favor intenta nuevamente en unos momentos."
        )


def _es_audio(content_type: str | None) -> bool:
    """Retorna True si el content type corresponde a un archivo de audio."""
    if not content_type:
        return False
    return content_type.startswith("audio/")
