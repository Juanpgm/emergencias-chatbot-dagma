# SKILL: Compresión de Contexto y Eficiencia de Tokens

## Cuándo usar

Siempre. Estas técnicas reducen el consumo de tokens y hacen las sesiones más económicas.

## Principios

### 1. Lecturas dirigidas, no exploratorias

- Leer rangos específicos de archivos en vez de archivos completos.
- Usar `grep_search` para localizar antes de `read_file`.
- Preferir `search_subagent` para exploración amplia.

### 2. Ediciones quirúrgicas

- Incluir contexto mínimo suficiente (3-5 líneas antes/después).
- Usar `multi_replace_string_in_file` para múltiples ediciones.
- Nunca leer un archivo completo solo para cambiar una línea.

### 3. Respuestas concisas

- No repetir código que el usuario ya puede ver.
- Confirmar cambios brevemente: "Actualizado X en Y".
- Omitir explicaciones obvias.

### 4. Memoria como caché

- Guardar decisiones arquitectónicas en CLAUDE.md.
- Guardar comandos descubiertos en TOOLS.md.
- Usar `.claude/rules/` para instrucciones por contexto de archivo.
- Preferir skills (carga bajo demanda) sobre rules (carga siempre).

### 5. Autodream — Sistema de memoria comprimida

- Al final de sesiones complejas, comprimir aprendizajes en notas concisas.
- Guardar en `/memories/session/` para la sesión actual.
- Promover insights durables a `/memories/` (user memory).
- Formato: bullets cortos, no prosa. Máximo 5 líneas por insight.

### 6. Paralelización

- Combinar lecturas independientes en una sola ronda de herramientas.
- Combinar ediciones independientes con `multi_replace_string_in_file`.
- No hacer búsquedas secuenciales cuando se puede buscar con regex alternado.

## Anti-patrones a evitar

- Leer archivos completos "por si acaso".
- Repetir el contenido de un archivo en la respuesta.
- Hacer búsquedas consecutivas de una sola palabra.
- Crear archivos `.md` de resumen no solicitados.
- Explicar cada paso antes de hacerlo.
