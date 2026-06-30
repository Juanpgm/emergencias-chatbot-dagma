from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from chatbot.app.core.redis import (
    delete_conversation,
    get_conversation,
    is_redis_available,
    set_conversation,
)
from chatbot.app.services.extraccion import (
    extraer_contacto,
    extraer_datos_emergencia,
    extraer_ubicacion,
)
from chatbot.app.services.persistencia import guardar_reporte
from chatbot.app.services.transcripcion import transcribir_audio
from shared.core.config import get_settings
from shared.core.database import get_db
from shared.schemas.emergencia import DatosEmergencia

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/webhook", tags=["WhatsApp"])

MENSAJES_TIPO = {
    "arbol_caido": "🌳 Arbol caido",
    "rescate_animales_silvestres": "🦜 Rescate de animal silvestre",
    "tala_arboles": "🪓 Tala de arboles",
    "contaminacion_fuente_hidrica": "💧 Contaminacion hidrica",
}

MENSAJE_BIENVENIDA = (
    "Hola 👋 Soy el asistente de emergencias ambientales del *DAGMA Cali*.\n\n"
    "Describe la situacion que quieres reportar. Por ejemplo:\n"
    '_"Hay un arbol caido sobre la carrera 8 con calle 15 en el barrio Granada, esta bloqueando el paso"_\n\n'
    "Tambien puedes enviarme una *nota de voz*.\n\n"
    "Tipos de emergencia que atiendo:\n"
    "🌳 Arboles caidos\n"
    "🦜 Rescate de animales silvestres\n"
    "🪓 Tala ilegal de arboles\n"
    "💧 Contaminacion de fuentes hidricas"
)

MENSAJE_PEDIR_DETALLES = (
    "Gracias por contactarnos 🙏\n\n"
    "Para registrar tu reporte necesito mas detalles. Por favor dime:\n\n"
    "📍 *Donde* ocurrio (direccion, barrio o punto de referencia)\n"
    "📝 *Que* paso exactamente\n\n"
    'Ejemplo:\n'
    '_"Hay un arbol caido sobre la carrera 8 con calle 15 en el barrio Granada, esta bloqueando el paso"_'
)

MENSAJE_ORIENTACION = (
    "Soy el asistente de emergencias ambientales del DAGMA Cali 🌿\n\n"
    "Puedo ayudarte a reportar:\n"
    "🌳 Arboles caidos\n"
    "🦜 Rescate de animales silvestres\n"
    "🪓 Tala ilegal de arboles\n"
    "💧 Contaminacion de fuentes hidricas\n\n"
    "Describe tu situacion y yo me encargo del resto."
)

MENSAJE_PEDIR_UBICACION = (
    "Entendido 📍\n\n"
    "Para completar tu reporte, necesito saber la *ubicacion* de la emergencia.\n"
    "Puedes enviarme la direccion, un barrio o un punto de referencia.\n\n"
    "Ejemplo: _\"Calle 5 # 23-10, barrio Granada\"_"
)

MENSAJE_PEDIR_CONTACTO = (
    "Entendido 🙏 Solo necesito tu *nombre completo* y *numero de telefono* "
    "para que el DAGMA pueda contactarte si es necesario.\n\n"
    "Si prefieres no compartirlos, escribe *\"anonimo\"*."
)

PALABRAS_VAGAS = frozenset({
    "no se", "nose", "no se", "no se nada", "nada", "algo", "ahi", "alli",
    "por ahi", "por ahi", "una cosa", "cosas", "raro", "extrano", "pues",
    "no tengo idea", "quien sabe", "quien sabe", "sabe",
})

PALABRAS_ANONIMO = frozenset({"anonimo", "anonima", "no gracias", "prefiero no"})


def _es_mensaje_vago(texto: str) -> bool:
    t = texto.lower().strip()
    return len(t) < 25 or t in PALABRAS_VAGAS


def _es_consulta_orientacion(texto: str) -> bool:
    t = texto.lower().strip()
    consultas = {
        "que haces", "quien eres", "ayuda", "help", "hola", "buenas",
        "buenos dias", "buenas tardes", "buenas noches", "que puedes hacer",
        "como funciona", "que es dagma",
    }
    return t in consultas


def _tiene_contacto(datos: DatosEmergencia) -> bool:
    return bool(datos.nombre_reportante or datos.telefono)


def _tiene_ubicacion(datos: DatosEmergencia) -> bool:
    if datos.latitud is not None and datos.longitud is not None:
        return True
    texto = (datos.direccion_hechos or "") + " " + (datos.ubicacion_inferida or "")
    return len(texto.strip()) >= 12


def _completar_telefono(datos: DatosEmergencia, wa_id: str):
    if not datos.telefono:
        datos.telefono = wa_id


async def _enviar_mensaje_whatsapp(to: str, texto: str):
    meta_token = settings.meta_whatsapp_token
    phone_number_id = settings.meta_whatsapp_phone_id
    if not meta_token or not phone_number_id:
        logger.info("Meta API no configurada. Mensaje no enviado a %s: %.80s", to, texto)
        return
    url = f"https://graph.facebook.com/v22.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {meta_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": texto},
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, headers=headers, json=payload)
        if not resp.is_success:
            logger.error("Meta API error: HTTP %d — %s", resp.status_code, resp.text[:200])
        else:
            logger.info("Mensaje enviado a %s via Meta API", to)


async def _responder(to: str, texto: str):
    await _enviar_mensaje_whatsapp(to, texto)


async def _confirmar_reporte(reporte, datos: DatosEmergencia, wa_id: str, sin_ubicacion: bool = False):
    tipo_label = MENSAJES_TIPO.get(datos.tipo_de_emergencia.value, datos.tipo_de_emergencia.value)
    ubicacion = datos.direccion_hechos or datos.ubicacion_inferida or "ubicacion no especificada"
    nombre_linea = f"*Reportante:* {datos.nombre_reportante}\n" if datos.nombre_reportante else ""
    nota = ""
    if sin_ubicacion:
        nota = "\n\n⚠️ _Registrado sin ubicacion precisa. Un funcionario DAGMA te contactara para confirmarla._"
    respuesta = (
        f"✅ *Reporte #{reporte.id} registrado en DAGMA*\n\n"
        f"{nombre_linea}"
        f"*Tipo:* {tipo_label}\n"
        f"*Ubicacion:* {ubicacion}\n\n"
        f"_{datos.descripcion_emergencia}_"
        f"{nota}\n\n"
        f"Un equipo del DAGMA atendera tu reporte. Gracias por cuidar el medio ambiente de Cali 🌿"
    )
    await _responder(wa_id, respuesta)


@router.get("/whatsapp")
async def verificar_webhook(
    hub_mode: str | None = Query(None, alias="hub.mode"),
    hub_challenge: str | None = Query(None, alias="hub.challenge"),
    hub_verify_token: str | None = Query(None, alias="hub.verify_token"),
):
    if hub_verify_token == settings.whatsapp_verify_token:
        return int(hub_challenge) if hub_challenge else "OK"
    raise HTTPException(status_code=403, detail="Token de verificacion invalido.")


@router.post("/whatsapp")
async def recibir_mensaje_whatsapp(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    wa_id, message_text, audio_url, latitude, longitude = _parse_meta_payload(body)
    if not wa_id:
        return JSONResponse(content={"status": "ignored"}, status_code=200)

    texto_nuevo = ""
    texto_original = ""
    tiene_gps = latitude is not None and longitude is not None

    try:
        if audio_url:
            logger.info("Procesando nota de voz de %s", wa_id)
            try:
                texto_nuevo = await transcribir_audio(audio_url)
                texto_original = f"[AUDIO TRANSCRITO] {texto_nuevo}"
            except Exception as exc:
                logger.error("Fallo al transcribir audio de %s: %s", wa_id, exc)
                await _responder(wa_id, (
                    "No pude procesar tu nota de voz 🎙️\n\n"
                    "Por favor escribe tu reporte en texto. Ejemplo:\n"
                    '_"Hay un arbol caido en la calle 5 con carrera 10, barrio Granada"_'
                ))
                return JSONResponse(content={"status": "error", "detail": str(exc)}, status_code=200)
        elif message_text:
            texto_nuevo = message_text.strip()
            texto_original = message_text.strip()

        pendiente = await get_conversation(wa_id)

        if pendiente and (texto_nuevo or tiene_gps):
            datos_dict = pendiente.get("datos", {})
            datos = DatosEmergencia(**datos_dict)

            if pendiente.get("esperando_contacto"):
                texto_lower = (texto_nuevo or "").lower().strip()
                es_anonimo = any(p in texto_lower for p in PALABRAS_ANONIMO)

                if not es_anonimo and texto_nuevo:
                    try:
                        contacto = await extraer_contacto(texto_nuevo)
                        if contacto.nombre_reportante:
                            datos.nombre_reportante = contacto.nombre_reportante
                        if contacto.telefono:
                            datos.telefono = contacto.telefono
                    except Exception as exc:
                        logger.warning("No se pudo extraer contacto de '%s': %s", texto_nuevo[:40], exc)

                _completar_telefono(datos, wa_id)
                if datos.nombre_reportante or es_anonimo or pendiente.get("intentos_contacto", 0) >= 1:
                    await delete_conversation(wa_id)
                    reporte = await guardar_reporte(
                        db=db, datos=datos,
                        whatsapp_from=wa_id,
                        texto_original=pendiente.get("texto_original", ""),
                    )
                    logger.info("Reporte #%d completado con contacto para %s", reporte.id, wa_id)
                    await _confirmar_reporte(reporte, datos, wa_id)
                    return JSONResponse(content={"status": "ok", "reporte_id": reporte.id}, status_code=200)
                else:
                    pendiente["intentos_contacto"] = pendiente.get("intentos_contacto", 0) + 1
                    await set_conversation(wa_id, pendiente)
                    await _responder(wa_id, MENSAJE_PEDIR_CONTACTO)
                    return JSONResponse(content={"status": "awaiting_contact"}, status_code=200)

            if tiene_gps:
                datos.latitud = latitude
                datos.longitud = longitude
                datos.ubicacion_inferida = f"GPS: {latitude}, {longitude}"
            elif texto_nuevo:
                try:
                    datos_ubicacion = await extraer_ubicacion(texto_nuevo)
                    if datos_ubicacion.direccion_hechos:
                        datos.direccion_hechos = datos_ubicacion.direccion_hechos
                    if datos_ubicacion.ubicacion_inferida:
                        datos.ubicacion_inferida = datos_ubicacion.ubicacion_inferida
                except Exception as exc:
                    logger.warning("extraer_ubicacion fallo ('%s'): %s", texto_nuevo[:40], exc)
                    datos.ubicacion_inferida = texto_nuevo

            if _tiene_ubicacion(datos):
                texto_orig_actualizado = pendiente.get("texto_original", "") + f" | UBICACION: {texto_nuevo}"
                await delete_conversation(wa_id)
                _completar_telefono(datos, wa_id)
                if not datos.nombre_reportante:
                    nueva_data = {
                        "datos": datos.model_dump(),
                        "texto_original": texto_orig_actualizado,
                        "esperando_contacto": True,
                        "intentos_ubicacion": 0,
                        "intentos_contacto": 0,
                    }
                    await set_conversation(wa_id, nueva_data)
                    await _responder(wa_id, MENSAJE_PEDIR_CONTACTO)
                    return JSONResponse(content={"status": "awaiting_contact"}, status_code=200)
                reporte = await guardar_reporte(
                    db=db, datos=datos,
                    whatsapp_from=wa_id,
                    texto_original=texto_orig_actualizado,
                )
                logger.info("Reporte #%d completado para %s", reporte.id, wa_id)
                await _confirmar_reporte(reporte, datos, wa_id)
                return JSONResponse(content={"status": "ok", "reporte_id": reporte.id}, status_code=200)
            else:
                pendiente["intentos_ubicacion"] = pendiente.get("intentos_ubicacion", 0) + 1
                if pendiente["intentos_ubicacion"] >= 2:
                    await delete_conversation(wa_id)
                    reporte = await guardar_reporte(
                        db=db, datos=datos,
                        whatsapp_from=wa_id,
                        texto_original=pendiente.get("texto_original", ""),
                    )
                    logger.info("Reporte #%d registrado sin ubicacion precisa para %s", reporte.id, wa_id)
                    await _confirmar_reporte(reporte, datos, wa_id, sin_ubicacion=True)
                    return JSONResponse(content={"status": "ok", "reporte_id": reporte.id}, status_code=200)
                await set_conversation(wa_id, pendiente)
                await _responder(wa_id, MENSAJE_PEDIR_UBICACION)
                return JSONResponse(content={"status": "awaiting_location"}, status_code=200)

        if not texto_nuevo and not tiene_gps:
            await _responder(wa_id, MENSAJE_BIENVENIDA)
            return JSONResponse(content={"status": "welcome"}, status_code=200)

        if texto_nuevo and _es_consulta_orientacion(texto_nuevo):
            await _responder(wa_id, MENSAJE_ORIENTACION)
            return JSONResponse(content={"status": "orientation"}, status_code=200)

        if texto_nuevo and _es_mensaje_vago(texto_nuevo):
            await _responder(wa_id, MENSAJE_PEDIR_DETALLES)
            return JSONResponse(content={"status": "ask_details"}, status_code=200)

        texto_para_llm = texto_nuevo
        if tiene_gps:
            texto_para_llm += f"\n\n[Ubicacion GPS: lat={latitude}, lon={longitude}]"

        try:
            datos = await extraer_datos_emergencia(texto_para_llm)
        except Exception as exc:
            logger.warning("LLM no pudo extraer datos de '%s...': %s", texto_nuevo[:50], exc)
            await _responder(wa_id, MENSAJE_ORIENTACION)
            return JSONResponse(content={"status": "llm_error"}, status_code=200)

        if tiene_gps:
            datos.latitud = latitude
            datos.longitud = longitude

        if not _tiene_ubicacion(datos):
            nueva_data = {
                "datos": datos.model_dump(),
                "texto_original": texto_original,
                "esperando_contacto": False,
                "intentos_ubicacion": 0,
                "intentos_contacto": 0,
            }
            await set_conversation(wa_id, nueva_data)
            tipo_label = MENSAJES_TIPO.get(datos.tipo_de_emergencia.value, "emergencia")
            await _responder(wa_id, (
                f"Entendido, recibi tu reporte sobre: *{tipo_label}*\n\n"
                + MENSAJE_PEDIR_UBICACION
            ))
            return JSONResponse(content={"status": "awaiting_location"}, status_code=200)

        _completar_telefono(datos, wa_id)
        if not datos.nombre_reportante:
            nueva_data = {
                "datos": datos.model_dump(),
                "texto_original": texto_original,
                "esperando_contacto": True,
                "intentos_ubicacion": 0,
                "intentos_contacto": 0,
            }
            await set_conversation(wa_id, nueva_data)
            await _responder(wa_id, MENSAJE_PEDIR_CONTACTO)
            return JSONResponse(content={"status": "awaiting_contact"}, status_code=200)

        reporte = await guardar_reporte(
            db=db, datos=datos,
            whatsapp_from=wa_id,
            texto_original=texto_original,
        )
        logger.info("Reporte #%d creado para %s", reporte.id, wa_id)
        await _confirmar_reporte(reporte, datos, wa_id)
        return JSONResponse(content={"status": "ok", "reporte_id": reporte.id}, status_code=200)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error procesando mensaje de %s: %s", wa_id, e)
        await delete_conversation(wa_id)
        await _responder(wa_id, (
            "Lo sentimos, ocurrio un error procesando tu reporte. "
            f"Por favor intenta nuevamente. (Error: {type(e).__name__})"
        ))
        return JSONResponse(content={"status": "error", "detail": str(e)}, status_code=200)


def _parse_meta_payload(body: dict) -> tuple:
    try:
        entry = body.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if not messages:
            return None, None, None, None, None

        msg = messages[0]
        wa_id = msg.get("from")
        msg_type = msg.get("type", "text")

        message_text = None
        audio_url = None
        latitude = None
        longitude = None

        if msg_type == "text":
            message_text = msg.get("text", {}).get("body", "")
        elif msg_type == "audio":
            audio_url = msg.get("audio", {}).get("id", "")
        elif msg_type == "location":
            location = msg.get("location", {})
            latitude = location.get("latitude")
            longitude = location.get("longitude")

        return wa_id, message_text, audio_url, latitude, longitude
    except Exception:
        logger.exception("Error parsing Meta payload: %.200s", str(body)[:200])
        return None, None, None, None, None
