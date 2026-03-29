# AGENTS.md — Agentes de Codificación

## Instrucciones generales para todos los agentes

Este proyecto es un backend **solo API** (sin interfaz gráfica) para atención de emergencias ambientales.

- **No crear** frontend, templates HTML, UI web ni CLI interactivo.

### Autonomía

- Ejecutar comandos, crear/editar archivos y correr tests SIN preguntar.
- Solo pedir confirmación en operaciones destructivas (borrar archivos, git push --force, drop tables).
- No preguntar "¿quieres que haga X?" — hacerlo directamente.

### Stack

- Python 3.11+ / FastAPI / Uvicorn
- SQLAlchemy async + PostgreSQL + PostGIS
- OpenAI Whisper + LangChain + GPT-4o
- Pydantic v2

### Reglas

- Código y comentarios en español.
- Async para todo I/O.
- Validar entrada en routers, lógica en services.
- Secrets en `.env`, acceder vía `get_settings()`.
- No loguear datos sensibles.

### Estructura

```
app/{core,schemas,models,services,routers}/
```

### Testing

- pytest + pytest-asyncio + httpx
- Mockear OpenAI y servicios externos
- Tests en `tests/`
