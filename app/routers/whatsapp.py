"""Router de webhook para recibir mensajes de WhatsApp (Twilio)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import httpx
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse

from app.core.config import get_settings
from app.core.database import get_db
from app.schemas.emergencia import DatosEmergencia
from app.services.extraccion import extraer_contacto, extraer_datos_emergencia, extraer_ubicacion
from app.services.persistencia import guardar_reporte
from app.services.transcripcion import transcribir_audio

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/webhook", tags=["WhatsApp"])


# ── Estado de conversación en memoria ─────────────────────────────────────────

@dataclass
class _ConversacionPendiente:
    """Datos parciales de un reporte en curso, esperando completar información faltante."""
    datos: DatosEmergencia
    texto_original: str
    intentos_ubicacion: int = 0
    esperando_contacto: bool = False
    intentos_contacto: int = 0


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

_MENSAJE_PEDIR_CONTACTO = (
    "Gracias por tu reporte 🙏 Para finalizarlo necesito tu *nombre completo*.\n\n"
    "Opcionalmente también puedes darme un número de teléfono adicional si deseas.\n\n"
    "_Estos datos permiten que un funcionario del DAGMA pueda contactarte si necesita "
    "más detalles para atender correctamente la emergencia. Tu número de WhatsApp "
    "ya quedará registrado como contacto principal._\n\n"
    "Si prefieres no dar tu nombre, responde *\"anónimo\"*."
)

_MENSAJE_ORIENTACION = (
    "Soy el asistente de emergencias ambientales del *DAGMA Cali* 🌿\n\n"
    "Puedes reportarme cualquiera de estas situaciones:\n\n"
    "🌳 *Árbol caído* — que bloquee una vía o represente peligro\n"
    "🦜 *Rescate de animal silvestre* — herido, atrapado o en peligro\n"
    "🪓 *Tala ilegal* — corte no autorizado de árboles nativos\n"
    "💧 *Contaminación hídrica* — ríos, quebradas o humedales afectados\n\n"
    "Para hacer tu reporte escríbeme *qué está pasando* y *dónde ocurre* en Cali.\n\n"
    "_Ejemplo: \"Hay un árbol caído sobre la carrera 8 con calle 15, barrio Granada\"_"
)

# Frases que indican un mensaje sin información útil
_FRASES_VAGAS = {
    "necesito reportar", "quiero reportar", "hola", "buenas", "buenos días",
    "buenas tardes", "buenas noches", "ayuda", "emergencia", "problema",
    "denuncia", "reportar", "quiero hacer un reporte", "como reportar",
    "necesito reportar una emergencia", "quiero reportar una emergencia",
}

# Fragmentos que indican pregunta de orientación sobre el servicio
_FRASES_ORIENTACION = {
    "para qué es", "para que es", "para qué sirve", "para que sirve",
    "qué es esto", "que es esto", "qué hace", "que hace", "qué puedo",
    "que puedo", "cómo funciona", "como funciona", "cómo se usa", "como se usa",
    "qué se puede", "que se puede", "qué reporto", "que reporto",
    "en qué te puedo", "en que te puedo", "qué tipos", "que tipos",
    "qué emergencias", "que emergencias",
}


def _es_mensaje_vago(texto: str) -> bool:
    """Retorna True si el texto es demasiado corto o vago para extraer datos."""
    t = texto.lower().strip()
    return len(t) < 25 or t in _FRASES_VAGAS


def _es_consulta_orientacion(texto: str) -> bool:
    """Retorna True si el mensaje es una pregunta sobre qué hace el servicio."""
    t = texto.lower().strip()
    if any(frase in t for frase in _FRASES_ORIENTACION):
        return True
    # Preguntas cortas genéricas (terminan en "?" y son < 60 chars)
    if t.endswith("?") and len(t) < 60:
        return True
    return False


_PALABRAS_ANONIMO = {
    "anónimo", "anonimo", "no quiero", "prefiero no", "sin datos",
    "no doy", "no deseo", "privado", "no dar", "confidencial",
}


def _tiene_contacto(datos: DatosEmergencia) -> bool:
    """Retorna True si el reporte tiene al menos nombre o teléfono."""
    return bool((datos.nombre_reportante or "").strip() or (datos.telefono or "").strip())


def _completar_telefono(datos: DatosEmergencia, whatsapp_from: str) -> None:
    """Si el reporte no tiene teléfono, usa el número de WhatsApp como fallback."""
    if not (datos.telefono or "").strip():
        # whatsapp_from tiene el formato "whatsapp:+573001234567" → extraer el número
        datos.telefono = whatsapp_from.removeprefix("whatsapp:")


def _tiene_ubicacion(datos: DatosEmergencia) -> bool:
    """Retorna True si el reporte tiene una ubicación útil y específica (no genérica)."""
    _PALABRAS_VAGAS = {
        "barrio", "calle", "carrera", "mi barrio", "mi casa", "mi casa",
        "aquí", "acá", "cerca", "el barrio", "la calle", "zona",
        "sector", "el sector", "la zona", "mi sector",
        "barrio del reportante", "no especificada", "ubicación no especificada",
        "desconocida", "no especificado", "sin ubicación", "sin dirección",
        "no se especifica", "no disponible",
    }

    if datos.latitud is not None and datos.longitud is not None:
        return True

    for campo in (datos.direccion_hechos, datos.ubicacion_inferida):
        valor = (campo or "").strip().lower()
        if valor and valor not in _PALABRAS_VAGAS and len(valor) >= 12:
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
    3. Si hay conversación pendiente (esperando ubicación o contacto), continúa el flujo.
    4. Si no hay pendiente: extrae datos con LLM.
    5. Si falta ubicación → pedir ubicación.
    6. Si falta contacto (nombre/teléfono) → pedir contacto.
    7. Con todos los datos → guardar en DB y confirmar.
    """
    await _validar_firma_twilio(request)

    texto_nuevo: str = ""
    texto_original: str = ""

    try:
        # ── 1. Obtener texto del mensaje ───────────────────────────────────
        if NumMedia > 0 and MediaUrl0 and _es_audio(MediaContentType0):
            logger.info("Procesando nota de voz de %s", From)
            try:
                texto_nuevo = await transcribir_audio(MediaUrl0)
                texto_original = f"[AUDIO TRANSCRITO] {texto_nuevo}"
            except httpx.HTTPStatusError as exc:
                logger.error("Fallo al transcribir audio de %s: HTTP %d", From, exc.response.status_code)
                return _twiml_response(
                    "No pude procesar tu nota de voz 🎙️\n\n"
                    "Por favor escribe tu reporte en texto. Ejemplo:\n"
                    "_\"Hay un árbol caído en la calle 5 con carrera 10, barrio Granada\"_"
                )
            except Exception as exc:
                logger.error("Error inesperado transcribiendo audio de %s: %s", From, exc)
                return _twiml_response(
                    "No pude procesar tu nota de voz 🎙️\n\n"
                    "Por favor escribe tu reporte en texto."
                )
        elif Body:
            texto_nuevo = Body.strip()
            texto_original = Body.strip()

        # Coordenadas GPS del mensaje
        tiene_gps = Latitude is not None and Longitude is not None

        # ── 2. ¿Hay una conversación pendiente? ───────────────────────────
        pendiente = _conversaciones.get(From)

        if pendiente and (texto_nuevo or tiene_gps):
            datos = pendiente.datos

            # ── 2a. Esperando datos de contacto ───────────────────────────
            if pendiente.esperando_contacto:
                texto_lower = (texto_nuevo or "").lower().strip()
                es_anonimo = any(p in texto_lower for p in _PALABRAS_ANONIMO)

                if not es_anonimo and texto_nuevo:
                    try:
                        contacto = await extraer_contacto(texto_nuevo)
                        if contacto.nombre_reportante:
                            datos.nombre_reportante = contacto.nombre_reportante
                        if contacto.telefono:
                            datos.telefono = contacto.telefono
                    except Exception as exc:
                        logger.warning("No se pudo extraer contacto de '%s': %s", texto_nuevo[:40], exc)

                _completar_telefono(datos, From)
                if datos.nombre_reportante or es_anonimo or pendiente.intentos_contacto >= 1:
                    del _conversaciones[From]
                    reporte = await guardar_reporte(
                        db=db, datos=datos,
                        whatsapp_from=From,
                        texto_original=pendiente.texto_original,
                    )
                    logger.info("Reporte #%d completado con contacto para %s", reporte.id, From)
                    return _twiml_confirmar(reporte, datos)
                else:
                    pendiente.intentos_contacto += 1
                    return _twiml_response(
                        "Entendido 🙏 Solo necesito tu *nombre completo* y *número de teléfono* "
                        "para que el DAGMA pueda contactarte si es necesario.\n\n"
                        "Si prefieres no compartirlos, escribe *\"anónimo\"*."
                    )

            # ── 2b. Esperando ubicación ────────────────────────────────────
            if tiene_gps:
                datos.latitud = Latitude
                datos.longitud = Longitude
                datos.ubicacion_inferida = f"GPS: {Latitude}, {Longitude}"
            elif texto_nuevo:
                try:
                    datos_ubicacion = await extraer_ubicacion(texto_nuevo)
                    if datos_ubicacion.direccion_hechos:
                        datos.direccion_hechos = datos_ubicacion.direccion_hechos
                    if datos_ubicacion.ubicacion_inferida:
                        datos.ubicacion_inferida = datos_ubicacion.ubicacion_inferida
                except Exception as exc:
                    logger.warning("extraer_ubicacion falló ('%s'): %s — usando texto directo", texto_nuevo[:40], exc)
                    datos.ubicacion_inferida = texto_nuevo

            if _tiene_ubicacion(datos):
                texto_orig_actualizado = pendiente.texto_original + f" | UBICACIÓN: {texto_nuevo}"
                del _conversaciones[From]
                _completar_telefono(datos, From)
                if not datos.nombre_reportante:
                    _conversaciones[From] = _ConversacionPendiente(
                        datos=datos,
                        texto_original=texto_orig_actualizado,
                        esperando_contacto=True,
                    )
                    return _twiml_response(_MENSAJE_PEDIR_CONTACTO)
                reporte = await guardar_reporte(
                    db=db, datos=datos,
                    whatsapp_from=From,
                    texto_original=texto_orig_actualizado,
                )
                logger.info("Reporte #%d completado para %s", reporte.id, From)
                return _twiml_confirmar(reporte, datos)
            else:
                pendiente.intentos_ubicacion += 1
                if pendiente.intentos_ubicacion >= 2:
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

        if _es_consulta_orientacion(texto_nuevo):
            return _twiml_response(_MENSAJE_ORIENTACION)

        texto_para_llm = texto_nuevo
        if tiene_gps:
            texto_para_llm += f"\n\n[Ubicación GPS: lat={Latitude}, lon={Longitude}]"

        # ── 4. Extraer datos con LLM ──────────────────────────────────────
        try:
            datos = await extraer_datos_emergencia(texto_para_llm)
        except Exception as exc:
            logger.warning("LLM no pudo extraer datos de '%s...': %s", texto_nuevo[:50], exc)
            return _twiml_response(_MENSAJE_ORIENTACION)

        if tiene_gps:
            datos.latitud = Latitude
            datos.longitud = Longitude

        # ── 5. ¿Tiene ubicación? ──────────────────────────────────────────
        if not _tiene_ubicacion(datos):
            _conversaciones[From] = _ConversacionPendiente(
                datos=datos,
                texto_original=texto_original,
            )
            tipo_label = _MENSAJES_TIPO.get(datos.tipo_de_emergencia.value, "emergencia")
            return _twiml_response(
                f"Entendido, recibí tu reporte sobre: *{tipo_label}*\n\n"
                + _MENSAJE_PEDIR_UBICACION
            )

        # ── 6. ¿Tiene nombre? (teléfono = WhatsApp como fallback) ────────────
        _completar_telefono(datos, From)
        if not datos.nombre_reportante:
            _conversaciones[From] = _ConversacionPendiente(
                datos=datos,
                texto_original=texto_original,
                esperando_contacto=True,
            )
            return _twiml_response(_MENSAJE_PEDIR_CONTACTO)

        # ── 7. Guardar en DB ──────────────────────────────────────────────
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

    nombre_linea = f"*Reportante:* {datos.nombre_reportante}\n" if datos.nombre_reportante else ""

    nota = ""
    if sin_ubicacion:
        nota = "\n\n⚠️ _Registrado sin ubicación precisa. Un funcionario DAGMA te contactará para confirmarla._"

    respuesta = (
        f"✅ *Reporte #{reporte.id} registrado en DAGMA*\n\n"
        f"{nombre_linea}"
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
