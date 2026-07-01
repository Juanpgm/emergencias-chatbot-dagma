"""Servicio de extracción de datos estructurados con LangChain + Groq (Llama 3.3 70B)."""

from __future__ import annotations

import logging

from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from shared.core.config import get_settings
from shared.schemas.emergencia import DatosContacto, DatosEmergencia, DatosUbicacion

logger = logging.getLogger(__name__)

settings = get_settings()

_llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    api_key=settings.groq_api_key,
)

_SYSTEM_PROMPT = """\
Eres un agente especializado del DAGMA (Departamento Administrativo de Gestión del Medio \
Ambiente) de Cali, Colombia. Recibes mensajes de ciudadanos colombianos reportando emergencias \
ambientales — escritos en español coloquial caleño, con abreviaturas, sin tildes y referencias \
locales. Tu tarea es extraer datos estructurados precisos.

TIPOS DE EMERGENCIA:

1. arbol_caido — árbol o rama caída que obstruye vías, daña propiedad o representa peligro.
   Señales: "se cayó", "palo caído", "árbol tumbado", "ramas bloqueando", "cayó encima".

2. rescate_animales_silvestres — animal silvestre herido, atrapado, abandonado o en peligro.
   Señales: "pájaro herido", "serpiente", "mico", "armadillo", "iguana", "lorito".
   NOTA: perros/gatos solo si hay riesgo real de vida.

3. tala_arboles — corte no autorizado o sospechoso de árboles o vegetación nativa.
   Señales: "están cortando", "talaron", "motosierra", "sin permiso", "deforestando".

4. contaminacion_fuente_hidrica — contaminación de ríos, quebradas, caños, humedales.
   Señales: "botando al río", "aceite en la quebrada", "aguas negras al caño", "derrame".

GRAVEDAD:
- alta → riesgo de vida, bloqueo vía principal, derrame químico, animal venenoso en zona habitada.
  Implica requiere_atencion_inmediata = true.
- media → árbol en vía secundaria, animal herido estable, contaminación puntual.
- baja → queja no urgente, poda sospechosa menor, basura en caño sin derrame.
requiere_atencion_inmediata = true si gravedad "alta" O el ciudadano usa: \
"urgente", "ya", "rápido", "bloqueando", "hay niños", "hay heridos".

EXTRACCIÓN DE UBICACIÓN (crítico — no dejar null si hay algún indicio):
Extrae CUALQUIER referencia geográfica: barrio, calle, carrera, número, comuna, conjunto, \
parque, colegio, supermercado, puente, avenida, punto de referencia.
Barrios de Cali: Aguablanca, Limonar, Granada, San Nicolás, El Centro, Chipichape, \
Terron Colorado, Siloé, Ciudad Córdoba, Ciudad Jardín, Pance, Cañasgordas, Floralia, \
Salomia, El Guabal, Valle del Lili, Univalle, Bosques del Limonar, entre muchos otros.
Cali tiene 22 comunas numeradas. Si el ciudadano la cita, inclúyela.
- "aquí en el Limonar" → ubicacion_inferida = "Barrio El Limonar"
- "carrera 5 con 10" → direccion_hechos = "Carrera 5 con Calle 10"
- Nunca dejes null ambos campos si hay alguna referencia geográfica en el texto.

OTRAS REGLAS:
- Extrae nombre, teléfono, email solo si están explícitamente en el texto.
- Si el reporte mezcla situaciones, clasifica la emergencia PRINCIPAL.
- descripcion_emergencia: máx. 2 oraciones directas.
- descripcion_detallada: contexto adicional inferido, 2-4 oraciones.
- Responde SOLO con el JSON estructurado. Sin texto adicional ni explicaciones.

EJEMPLO:
Texto: "oiga hay un palo enorme caido en la 8 con 15 en el granada ta bloqueando los carros \
soy Carlos Perez cel 3001234567"
JSON: {"nombre_reportante":"Carlos Pérez","telefono":"3001234567","email":null,\
"direccion_hechos":"Carrera 8 con Calle 15","direccion_persona":null,\
"tipo_de_emergencia":"arbol_caido",\
"descripcion_emergencia":"Árbol caído bloquea la Carrera 8 con Calle 15 en Granada.",\
"descripcion_detallada":"Un árbol de gran tamaño obstruye el tráfico vehicular en el barrio Granada. La vía está completamente bloqueada.",\
"ubicacion_inferida":"Barrio Granada","latitud":null,"longitud":null,\
"nivel_de_gravedad":"alta","requiere_atencion_inmediata":true}
"""

_prompt = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM_PROMPT),
    ("human", "Analiza el siguiente reporte de emergencia ambiental:\n\n{texto}"),
])

_chain = _prompt | _llm.with_structured_output(DatosEmergencia)

_SYSTEM_CONTACTO = """\
Extrae del texto el nombre completo y el número de teléfono de una persona colombiana.
El texto puede estar en español coloquial. Solo usa lo que esté explícitamente en el texto.
- Teléfonos colombianos: 10 dígitos, empiezan por 3 (celular) o por 60 (fijo Cali).
- Puede estar escrito como "cel 3001234567", "mi número es 300 123 4567", "al 3001234567".
- Nombres pueden estar abreviados o sin tildes.
Si no hay nombre o teléfono, deja el campo en null.
"""

_prompt_contacto = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM_CONTACTO),
    ("human", "{texto}"),
])

_chain_contacto = _prompt_contacto | _llm.with_structured_output(DatosContacto)


async def extraer_datos_emergencia(texto: str) -> DatosEmergencia:
    """Analiza *texto* con Llama 3.3 70B (Groq) y retorna un :class:`DatosEmergencia` poblado."""
    logger.info("Extrayendo datos de emergencia (%d caracteres)", len(texto))
    resultado: DatosEmergencia = await _chain.ainvoke({"texto": texto})
    logger.info(
        "Extracción exitosa: tipo=%s, gravedad=%s",
        resultado.tipo_de_emergencia.value,
        resultado.nivel_de_gravedad.value,
    )
    return resultado


async def extraer_contacto(texto: str) -> DatosContacto:
    """Extrae nombre y teléfono de un mensaje de respuesta del ciudadano."""
    logger.info("Extrayendo contacto (%d caracteres)", len(texto))
    return await _chain_contacto.ainvoke({"texto": texto})


_SYSTEM_UBICACION = """\
Extrae del texto la dirección o ubicación donde ocurre una emergencia ambiental en Cali, Colombia.
El texto puede ser la respuesta de un ciudadano a la pregunta "¿dónde ocurre?", en español coloquial.

Devuelve:
- direccion_hechos: dirección exacta si la hay (calle, carrera, número, avenida)
- ubicacion_inferida: barrio, comuna, punto de referencia, lugar conocido

Barrios de Cali: Aguablanca, Limonar, Granada, San Nicolás, El Centro, Chipichape, Terron Colorado,
Siloé, Ciudad Córdoba, Ciudad Jardín, Pance, Cañasgordas, Floralia, Salomia, El Guabal, Univalle.
Cali tiene 22 comunas numeradas.

Extrae CUALQUIER referencia geográfica, aunque sea informal:
- "cerca del éxito de Calima" → ubicacion_inferida = "Sector Éxito de Calima"
- "en el parque de las banderas" → ubicacion_inferida = "Parque de las Banderas"
- "por la 80" → ubicacion_inferida = "Avenida 80"
Solo deja null si realmente no hay ninguna referencia geográfica.
"""

_prompt_ubicacion = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM_UBICACION),
    ("human", "{contexto}{texto}"),
])

_chain_ubicacion = _prompt_ubicacion | _llm.with_structured_output(DatosUbicacion)


async def extraer_ubicacion(texto: str, contexto_reporte: str | None = None) -> DatosUbicacion:
    """Extrae dirección y ubicación inferida de un mensaje de seguimiento.

    contexto_reporte: descripción original del reporte (ayuda al LLM a inferir ubicación
    si el ciudadano da una respuesta corta como "aquí en el Limonar").
    """
    logger.info("Extrayendo ubicación (%d caracteres)", len(texto))
    prefijo = f"[Contexto del reporte: {contexto_reporte}]\n\nRespuesta del ciudadano: " if contexto_reporte else ""
    return await _chain_ubicacion.ainvoke({"contexto": prefijo, "texto": texto})
