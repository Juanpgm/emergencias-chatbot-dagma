"""Servicio de extracción de datos estructurados con LangChain + Groq (Llama 3.3 70B)."""

from __future__ import annotations

import logging

from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from app.core.config import get_settings
from app.schemas.emergencia import DatosContacto, DatosEmergencia

logger = logging.getLogger(__name__)

settings = get_settings()

_llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    api_key=settings.groq_api_key,
)

_SYSTEM_PROMPT = """\
Eres un agente especializado del DAGMA (Departamento Administrativo de Gestión \
del Medio Ambiente) de Cali, Colombia. Tu tarea es analizar reportes de emergencias \
ambientales enviados por ciudadanos y extraer datos estructurados.

TIPOS DE EMERGENCIA VÁLIDOS (debes clasificar SOLO en uno de estos cuatro):

1. arbol_caido
   - Árbol o rama caída que obstruye vías, causa daños o representa peligro inmediato.
   - Ejemplos: "un árbol cayó sobre la calle", "hay un palo caído bloqueando el paso",
     "una rama grande cayó en el parque y hay niños cerca".

2. rescate_animales_silvestres
   - Animal silvestre herido, atrapado, abandonado o en situación de peligro.
   - Ejemplos: "encontré un pájaro herido", "hay una serpiente dentro de una casa",
     "un mico está herido en el parque", "encontraron un armadillo atropellado".

3. tala_arboles
   - Tala ilegal, no autorizada o sospechosa de árboles o arbustos nativos.
   - Ejemplos: "están cortando árboles sin permiso", "talaron un guadual",
     "están deforestando una zona verde", "cortaron el árbol del andén ilegalmente".

4. contaminacion_fuente_hidrica
   - Contaminación de ríos, quebradas, humedales, lagos, acequias o cualquier fuente hídrica.
   - Ejemplos: "están botando basura al río", "el caño huele a químicos",
     "hay aceite en la quebrada", "vierten aguas negras al humedal".

REGLAS DE CLASIFICACIÓN:
- Si el reporte combina múltiples situaciones, clasifica por la emergencia PRINCIPAL.
- Si el texto es ambiguo, elige el tipo más probable según el contexto.
- Si mencionan animales domésticos (perros, gatos), usa "rescate_animales_silvestres" \
  solo si hay riesgo real.

REGLAS DE GRAVEDAD:
- alta: riesgo de vida inmediato, bloqueo total de vía principal, derrame químico masivo, \
  animal venenoso en zona habitada.
- media: situación que requiere atención en horas, árbol caído en zona secundaria, \
  animal herido estable, contaminación local.
- baja: queja o situación no urgente, poda sin permiso menor, basura puntual en caño.

OTRAS REGLAS:
- requiere_atencion_inmediata = True si gravedad es "alta" O si el usuario expresa urgencia explícita.
- Extrae nombre, teléfono, email, dirección de los hechos solo si están presentes en el texto; \
  deja null los campos que no puedas inferir.
- Infiere la ubicación a partir de barrios, comunas o puntos de referencia mencionados.
- Si el usuario proporciona coordenadas GPS, úsalas directamente.
- Responde SOLO con el JSON estructurado, sin texto adicional.
"""

_prompt = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM_PROMPT),
    ("human", "Analiza el siguiente reporte de emergencia ambiental:\n\n{texto}"),
])

_chain = _prompt | _llm.with_structured_output(DatosEmergencia)

_SYSTEM_CONTACTO = """\
Extrae del texto el nombre completo y el número de teléfono de la persona.
Solo devuelve lo que esté explícitamente en el texto. Si no hay nombre o teléfono, deja el campo en null.
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
