# Autodream — Sistema de Memoria y Compresión de Contexto

## Concepto

Autodream es un patrón de gestión de memoria para agentes IA que permite:

1. **Comprimir** el contexto de trabajo en notas concisas al final de cada sesión.
2. **Recordar** decisiones y patrones entre sesiones sin recargar todo el historial.
3. **Soñar** — generar insights comprimidos que se guardan para sesiones futuras.

## Cómo funciona en este proyecto

### Niveles de memoria

```
/memories/                    ← User memory (persistente, cross-proyecto)
├── patterns.md               ← Patrones generales de desarrollo
├── debugging.md              ← Técnicas de debugging descubiertas
└── preferences.md            ← Preferencias del usuario

/memories/session/            ← Session memory (solo esta conversación)
├── current-task.md           ← Estado actual del trabajo
├── decisions.md              ← Decisiones tomadas en esta sesión
└── blockers.md               ← Problemas encontrados y soluciones

/memories/repo/               ← Repo memory (scope del workspace)
└── architecture-decisions.md ← ADRs comprimidas
```

### Protocolo de Autodream

#### Al inicio de sesión

1. Leer `/memories/` para cargar contexto persistente.
2. Verificar si hay session memory previa relevante.
3. Cargar CLAUDE.md y rules automáticamente.

#### Durante la sesión

1. Ante cada decisión significativa → anotar en session memory.
2. Ante cada error resuelto → evaluar si merece user memory.
3. Mantener máximo 200 líneas en user memory.

#### Al final de sesión (Dream phase)

1. **Comprimir**: Resumir la sesión en 5-10 bullets.
2. **Clasificar**: ¿Es insight local (session) o duradero (user/repo)?
3. **Guardar**: Escribir notas comprimidas en el nivel apropiado.
4. **Limpiar**: Eliminar session memory que ya no sea útil.

### Formato de notas de memoria

```markdown
## [Fecha] Tema

- Insight conciso en una línea
- Otro insight
- Comando descubierto: `alembic upgrade head`
- Patrón: usar X en vez de Y porque Z
```

### Reglas

- Máximo 5 líneas por insight.
- Usar bullets, no prosa.
- Incluir ejemplo concreto cuando sea relevante.
- No duplicar info que ya esté en CLAUDE.md o rules.
- Priorizar: errores evitados > patrones exitosos > preferencias.

## Compresión de contexto

### Técnicas implementadas

1. **Rules por path**: Solo cargan cuando se trabaja con archivos que coinciden.
2. **Skills on-demand**: Se cargan solo cuando la tarea lo requiere.
3. **Memory tiering**: User memory siempre cargada (200 líneas); session y repo bajo demanda.
4. **CLAUDE.md conciso**: < 200 líneas, bullets directos.
5. **Imports selectivos**: `@archivo` para cargar contexto solo cuando se necesita.

### Métricas de eficiencia

- CLAUDE.md: ~50 líneas (objetivo < 200)
- Rules: 6 archivos × ~10 líneas = ~60 líneas (carga por path)
- Skills: 7 archivos (carga on-demand, no al inicio)
- User memory: objetivo < 100 líneas
