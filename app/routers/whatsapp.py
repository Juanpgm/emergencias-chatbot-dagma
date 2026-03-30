"""Router de webhook para recibir mensajes de WhatsApp (Twilio)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse

from app.core.config import get_settings
from app.core.database import get_db
from app.schemas.emergencia import DatosEmergencia
from app.services.extraccion import extraer_datos_emergencia
from app.services.persistencia import guardar_reporte
from app.services.transcripcion import transcribir_audio

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/webhook", tags=["WhatsApp"])


# ── Estado de conversación en memoria ─────────────────────────────────────────

@dataclass
class _ConversacionPendiente:
    """Datos parciales de un reporte en curso, esperando completar la ubicación."""
    datos: DatosEmergencia
    texto_original: str
    intentos_ubicacion: int = 0


# Diccionario keyed por número de WhatsApp (whatsapp:+57...)
_conversaciones: dict[str, _ConversacionPendiente] = {}


# ── Mensajes al usuario ────────────────────────────────────────────────────────

_MENSAJE_BIENVENIDA = (
    "Hola 👋 Soy el asistente de emergencias ambientales del *DAGMA Cali*.\n\n"
    "Por favor cuéntame qué está pasando. Puedes describirlo con texto o enviar una nota de voz.\n\n"
    "Atendemos:\n"
    "🌳 Árboles caídos\n"
    "🦜 Rescate de animales silvestres\n"
    "🪓 Tala ilegal de árboles\n"
    "💧 Contaminación de fuentes hídricas"
)

_MENSAJE_PEDIR_DETALLES = (
    "Gracias por contactarnos 🙏\n\n"
    "Para registrar tu reporte necesito más información. Por favor indícame:\n\n"
    "1️⃣ *¿Qué está pasando?* (describe la situación)\n"
    "2️⃣ *¿Dónde ocurre?* (dirección, barrio o punto de referencia en Cali)\n\n"
    "*Ejemplo:* \"Hay un árbol caído sobre la carrera 8 con calle 15 en el barrio Granada, está bloqueando el paso\""
)

_MENSAJE_PEDIR_UBICACION = (
    "Entendido 📍 Para completar tu reporte necesito saber *exactamente dónde* ocurre la emergencia.\n\n"
    "Por favor indícame:\n"
    "• Dirección (carrera/calle)\n"
    "• Barrio o comuna\n"
    "• O un punto de referencia conocido\n\n"
    "También puedes *compartir tu ubicación GPS* desde WhatsApp 📌"
)

# Frases que indican un mensaje sin información útil
_FRASES_VAGAS = {
    "necesito reportar", "quiero reportar", "hola", "buenas", "buenos días",
    "buenas tardes", "buenas noches", "ayuda", "emergencia", "problema",
    "denuncia", "reportar", "quiero hacer un reporte", "como reportar",
    "necesito reportar una emergencia", "quiero reportar una emergencia",
}


def _es_mensaje_vago(texto: str) -> bool:
    """Retorna True si el texto es demasiado corto o vago para extraer datos."""
    t = texto.lower().strip()
    return len(t) < 25 or t in _FRASES_VAGAS


def _tiene_ubicacion(datos: DatosEmergencia) -> bool:
    """Retorna True si el reporte tiene una ubicación útil (no genérica)."""
    ubicaciones_vagas = {
        None, "", "barrio del reportante", "no especificada", "ubicación no especificada",
        "desconocida", "no especificado", "sin ubicación", "sin dirección",
    }
    dir_hechos = (datos.direccion_hechos or "").strip().lower()
    ub_inferida = (datos.ubicacion_inferida or "").strip().lower()

    if datos.latitud is not None and datos.longitud is not None:
        return True
    if dir_hechos and dir_hechos not in ubicaciones_vagas and len(dir_hechos) > 5:
        return True
    if ub_inferida and ub_inferida not in ubicaciones_vagas and len(ub_inferida) > 5:
        return True
    return False


def _twiml_response(mensaje: str) -> Response:
    """Construye una respuesta TwiML con el texto dado para enviar al usuario por WhatsApp."""
    resp = MessagingResponse()
    resp.message(mensaje)
    return Response(content=str(resp), media_type="application/xml")


# ── Validación de firma Twilio ─────────────────────────────────────────────────

async def _validar_firma_twilio(request: Request) -> None:
    """Verifica que la petición viene realmente de Twilio.

    Solo activa la validación cuando auth_token está configurado.
    En desarrollo sin auth_token, omite la validación.
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

    Flujo conversacional:
    1. Valida firma Twilio.
    2. Transcribe audio si aplica.
    3. Si hay una conversación pendiente (falta ubicación), intenta completarla.
    4. Si no hay pendiente: extrae datos con LLM.
    5. Si faltan datos clave (ubicación), guarda en memoria y pide al usuario.
    6. Cuando hay datos completos, guarda en DB y confirma al usuario.
    """
    await _validar_firma_twilio(request)

    texto_nuevo: str = ""
    texto_original: str = ""

    try:
        # ── 1. Obtener texto del mensaje ───────────────────────────────────
        if NumMedia > 0 and MediaUrl0 and _es_audio(MediaContentType0):
            logger.info("Procesando nota de voz de %s", From)
            texto_nuevo = await transcribir_audio(MediaUrl0)
            texto_original = f"[AUDIO TRANSCRITO] {texto_nuevo}"
        elif Body:
            texto_nuevo = Body.strip()
            texto_original = Body.strip()

        # Coordenadas GPS del mensaje
        tiene_gps = Latitude is not None and Longitude is not None

        # ── 2. ¿Hay una conversación pendiente esperando ubicación? ────────
        pendiente = _conversaciones.get(From)

        if pendiente and (texto_nuevo or tiene_gps):
            # El usuario respondió con su ubicación (o GPS)
            datos = pendiente.datos

            if tiene_gps:
                datos.latitud = Latitude
                datos.longitud = Longitude
                datos.ubicacion_inferida = f"GPS: {Latitude}, {Longitude}"
            elif texto_nuevo:
                # Re-extraer solo para obtener la ubicación del texto nuevo
                datos_ubicacion = await extraer_datos_emergencia(
                    f"Ubicación de la emergencia: {texto_nuevo}"
                )
                if datos_ubicacion.direccion_hechos:
                    datos.direccion_hechos = datos_ubicacion.direccion_hechos
                if datos_ubicacion.ubicacion_inferida:
                    datos.ubicacion_inferida = datos_ubicacion.ubicacion_inferida

            if _tiene_ubicacion(datos):
                # Tenemos ubicación — registrar y limpiar estado
                del _conversaciones[From]
                reporte = await guardar_reporte(
                    db=db, datos=datos,
                    whatsapp_from=From,
                    texto_original=pendiente.texto_original + f" | UBICACIÓN: {texto_nuevo}",
                )
                logger.info("Reporte #%d completado para %s", reporte.id, From)
                return _twiml_confirmar(reporte, datos)
            else:
                # Todavía sin ubicación útil
                pendiente.intentos_ubicacion += 1
                if pendiente.intentos_ubicacion >= 2:
                    # Después de 2 intentos, registrar con lo que hay
                    del _conversaciones[From]
                    reporte = await guardar_reporte(
                        db=db, datos=datos,
                        whatsapp_from=From,
                        texto_original=pendiente.texto_original,
                    )
                    logger.info("Reporte #%d registrado sin ubicación precisa para %s", reporte.id, From)
                    return _twiml_confirmar(reporte, datos, sin_ubicacion=True)
                return _twiml_response(_MENSAJE_PEDIR_UBICACION)

        # ── 3. Mensaje nuevo sin conversación pendiente ────────────────────
        if not texto_nuevo and not tiene_gps:
            return _twiml_response(_MENSAJE_BIENVENIDA)

        if _es_mensaje_vago(texto_nuevo):
            return _twiml_response(_MENSAJE_PEDIR_DETALLES)

        texto_para_llm = texto_nuevo
        if tiene_gps:
            texto_para_llm += f"\n\n[Ubicación GPS: lat={Latitude}, lon={Longitude}]"

        # ── 4. Extraer datos con LLM ──────────────────────────────────────
        datos = await extraer_datos_emergencia(texto_para_llm)

        if tiene_gps:
            datos.latitud = Latitude
            datos.longitud = Longitude

        # ── 5. ¿Tiene ubicación? ──────────────────────────────────────────
        if not _tiene_ubicacion(datos):
            # Guardar estado y pedir ubicación
            _conversaciones[From] = _ConversacionPendiente(
                datos=datos,
                texto_original=texto_original,
            )
            tipo_label = _MENSAJES_TIPO.get(datos.tipo_de_emergencia.value, "emergencia")
            return _twiml_response(
                f"Entendido, recibí tu reporte sobre: *{tipo_label}*\n\n"
                + _MENSAJE_PEDIR_UBICACION
            )

        # ── 6. Guardar en DB ──────────────────────────────────────────────
        reporte = await guardar_reporte(
            db=db, datos=datos,
            whatsapp_from=From,
            texto_original=texto_original,
        )
        logger.info("Reporte #%d creado para %s", reporte.id, From)
        return _twiml_confirmar(reporte, datos)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error procesando mensaje de %s: %s", From, e)
        # Limpiar conversación pendiente en caso de error
        _conversaciones.pop(From, None)
        return _twiml_response(
            "Lo sentimos, ocurrió un error procesando tu reporte. "
            f"Por favor intenta nuevamente. (Error: {type(e).__name__})"
        )


def _twiml_confirmar(reporte, datos: DatosEmergencia, sin_ubicacion: bool = False) -> Response:
    """Construye la respuesta de confirmación de reporte registrado."""
    tipo_label = _MENSAJES_TIPO.get(datos.tipo_de_emergencia.value, datos.tipo_de_emergencia.value)
    gravedad_label = _MENSAJES_GRAVEDAD.get(datos.nivel_de_gravedad.value, datos.nivel_de_gravedad.value)
    ubicacion = datos.direccion_hechos or datos.ubicacion_inferida or "ubicación no especificada"

    nota = ""
    if sin_ubicacion:
        nota = "\n\n⚠️ _Registrado sin ubicación precisa. Un funcionario DAGMA te contactará para confirmarla._"

    respuesta = (
        f"✅ *Reporte #{reporte.id} registrado en DAGMA*\n\n"
        f"*Tipo:* {tipo_label}\n"
        f"*Gravedad:* {gravedad_label}\n"
        f"*Ubicación:* {ubicacion}\n\n"
        f"_{datos.descripcion_emergencia}_"
        f"{nota}\n\n"
        f"Un equipo del DAGMA atenderá tu reporte. Gracias por cuidar el medio ambiente de Cali 🌿"
    )
    return _twiml_response(respuesta)


def _es_audio(content_type: str | None) -> bool:
    """Retorna True si el content type corresponde a un archivo de audio."""
    if not content_type:
        return False
    return content_type.startswith("audio/")
