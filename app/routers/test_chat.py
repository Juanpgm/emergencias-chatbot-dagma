"""Endpoint de prueba público para testear el bot sin WhatsApp."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from shared.core.database import get_db
from app.services.extraccion import extraer_contacto, extraer_datos_emergencia, extraer_ubicacion
from app.services.persistencia import guardar_reporte
from app.routers.whatsapp import (
    _MENSAJE_BIENVENIDA,
    _MENSAJE_ORIENTACION,
    _MENSAJE_PEDIR_CONTACTO,
    _MENSAJE_PEDIR_DETALLES,
    _MENSAJE_PEDIR_UBICACION,
    _MENSAJES_GRAVEDAD,
    _MENSAJES_TIPO,
    _ConversacionPendiente,
    _completar_telefono,
    _conversaciones,
    _es_consulta_orientacion,
    _es_mensaje_vago,
    _tiene_ubicacion,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/test", tags=["Test"])

_PALABRAS_ANONIMO_SET = {
    "anónimo", "anonimo", "no quiero", "prefiero no",
    "sin datos", "privado", "no dar",
}


class ChatRequest(BaseModel):
    message: str
    phone: str = "+57300000000"
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    reporte_id: int | None = None
    tipo: str | None = None
    gravedad: str | None = None


def _confirmar(reporte, datos, session_id: str) -> ChatResponse:
    tipo = _MENSAJES_TIPO.get(datos.tipo_de_emergencia.value, datos.tipo_de_emergencia.value)
    gravedad = _MENSAJES_GRAVEDAD.get(datos.nivel_de_gravedad.value, datos.nivel_de_gravedad.value)
    ubicacion = datos.direccion_hechos or datos.ubicacion_inferida or "no especificada"
    nombre = f"Reportante: {datos.nombre_reportante}\n" if datos.nombre_reportante else ""
    return ChatResponse(
        reply=(
            f"✅ Reporte #{reporte.id} registrado en DAGMA\n\n"
            f"{nombre}"
            f"Tipo: {tipo}\n"
            f"Gravedad: {gravedad}\n"
            f"Ubicación: {ubicacion}\n\n"
            f"{datos.descripcion_emergencia}"
        ),
        session_id=session_id,
        reporte_id=reporte.id,
        tipo=datos.tipo_de_emergencia.value,
        gravedad=datos.nivel_de_gravedad.value,
    )


@router.post("/chat", response_model=ChatResponse)
async def test_chat(body: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Simula una conversación con el bot sin WhatsApp.

    Mantiene estado multi-turno via session_id. Omitir session_id inicia
    una conversación nueva. Pasar el mismo session_id continúa la sesión.
    """
    sid = body.session_id or str(uuid.uuid4())
    from_key = f"test:{sid}"
    texto = body.message.strip()

    if not texto:
        return ChatResponse(reply=_MENSAJE_BIENVENIDA, session_id=sid)

    pendiente = _conversaciones.get(from_key)

    # ── Conversación pendiente ──────────────────────────────────────────────────
    if pendiente:
        datos = pendiente.datos

        if pendiente.esperando_contacto:
            es_anonimo = any(p in texto.lower() for p in _PALABRAS_ANONIMO_SET)
            if not es_anonimo:
                try:
                    contacto = await extraer_contacto(texto)
                    if contacto.nombre_reportante:
                        datos.nombre_reportante = contacto.nombre_reportante
                    if contacto.telefono:
                        datos.telefono = contacto.telefono
                except Exception:
                    pass

            _completar_telefono(datos, from_key)
            if datos.nombre_reportante or es_anonimo or pendiente.intentos_contacto >= 1:
                del _conversaciones[from_key]
                reporte = await guardar_reporte(db=db, datos=datos, whatsapp_from=body.phone, texto_original=pendiente.texto_original)
                return _confirmar(reporte, datos, sid)

            pendiente.intentos_contacto += 1
            return ChatResponse(reply=_MENSAJE_PEDIR_CONTACTO, session_id=sid)

        # Esperando ubicación
        try:
            ub = await extraer_ubicacion(texto, contexto_reporte=pendiente.texto_original)
            if ub.direccion_hechos:
                datos.direccion_hechos = ub.direccion_hechos
            if ub.ubicacion_inferida:
                datos.ubicacion_inferida = ub.ubicacion_inferida
        except Exception:
            datos.ubicacion_inferida = texto

        if _tiene_ubicacion(datos):
            del _conversaciones[from_key]
            _completar_telefono(datos, from_key)
            if not datos.nombre_reportante:
                _conversaciones[from_key] = _ConversacionPendiente(
                    datos=datos,
                    texto_original=pendiente.texto_original + f" | UBICACIÓN: {texto}",
                    esperando_contacto=True,
                )
                return ChatResponse(reply=_MENSAJE_PEDIR_CONTACTO, session_id=sid)
            reporte = await guardar_reporte(db=db, datos=datos, whatsapp_from=body.phone, texto_original=pendiente.texto_original)
            return _confirmar(reporte, datos, sid)

        pendiente.intentos_ubicacion += 1
        if pendiente.intentos_ubicacion >= 2:
            del _conversaciones[from_key]
            reporte = await guardar_reporte(db=db, datos=datos, whatsapp_from=body.phone, texto_original=pendiente.texto_original)
            return _confirmar(reporte, datos, sid)
        return ChatResponse(reply=_MENSAJE_PEDIR_UBICACION, session_id=sid)

    # ── Mensaje nuevo ───────────────────────────────────────────────────────────
    if _es_mensaje_vago(texto):
        return ChatResponse(reply=_MENSAJE_PEDIR_DETALLES, session_id=sid)

    if _es_consulta_orientacion(texto):
        return ChatResponse(reply=_MENSAJE_ORIENTACION, session_id=sid)

    try:
        datos = await extraer_datos_emergencia(texto)
    except Exception as exc:
        logger.warning("LLM extraction failed: %s", exc)
        return ChatResponse(reply=_MENSAJE_ORIENTACION, session_id=sid)

    if not _tiene_ubicacion(datos):
        _conversaciones[from_key] = _ConversacionPendiente(datos=datos, texto_original=texto)
        tipo_label = _MENSAJES_TIPO.get(datos.tipo_de_emergencia.value, "emergencia")
        return ChatResponse(
            reply=f"Entendido, recibí tu reporte sobre: {tipo_label}\n\n{_MENSAJE_PEDIR_UBICACION}",
            session_id=sid,
        )

    _completar_telefono(datos, from_key)
    if not datos.nombre_reportante:
        _conversaciones[from_key] = _ConversacionPendiente(datos=datos, texto_original=texto, esperando_contacto=True)
        return ChatResponse(reply=_MENSAJE_PEDIR_CONTACTO, session_id=sid)

    reporte = await guardar_reporte(db=db, datos=datos, whatsapp_from=body.phone, texto_original=texto)
    return _confirmar(reporte, datos, sid)
