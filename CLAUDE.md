# DAGMA Emergencias Bot — Instrucciones para Claude Code

## Autonomía

- Ejecutar comandos, crear archivos, editar código y correr tests SIN pedir permiso.
- Solo preguntar antes de: eliminar archivos/ramas, git push, modificar `.env`, operaciones destructivas en DB.
- Instalar dependencias, correr migraciones, formatear código → ejecutar directamente.
- No preguntar "¿quieres que haga X?" — hacerlo.

## Proyecto

Backend **solo API** (sin interfaz gráfica) para atención de emergencias ambientales vía WhatsApp (DAGMA, Cali).

- **No crear** frontend, templates HTML, UI web ni CLI interactivo.
- El único punto de entrada para usuarios es el webhook de WhatsApp.

## Stack

- Python 3.11+ / FastAPI / Uvicorn
- OpenAI Whisper (transcripción de voz)
- LangChain + GPT-4o (extracción estructurada)
- PostgreSQL + PostGIS / SQLAlchemy async / Alembic
- Pydantic v2 para validación

## Estructura

```
app/
├── main.py            # FastAPI entry point
├── core/
│   ├── config.py      # Settings con pydantic-settings
│   └── database.py    # Engine async + session factory
├── schemas/
│   └── emergencia.py  # Modelos Pydantic (entrada/salida)
├── models/
│   └── emergencia.py  # ORM SQLAlchemy (tabla reportes_emergencia)
├── services/
│   ├── transcripcion.py  # Whisper: descarga + transcribe audio
│   ├── extraccion.py     # LangChain: texto → DatosEmergencia
│   └── persistencia.py   # Guarda reportes en DB
└── routers/
    └── whatsapp.py    # POST /webhook/whatsapp
```

## Comandos

- Instalar deps: `pip install -r requirements.txt`
- Ejecutar dev: `uvicorn app.main:app --reload --port 8000`
- Migración nueva: `alembic revision --autogenerate -m "descripcion"`
- Aplicar migraciones: `alembic upgrade head`
- Tests: `pytest tests/ -v`

## Convenciones

- Todo el código y comentarios en español donde sea legible; docstrings en español.
- Funciones async para I/O (DB, HTTP, APIs).
- Separar routers/, services/, schemas/, models/.
- Usar `from __future__ import annotations` en todos los módulos.
- Tipos explícitos; `Optional[X]` → `X | None` con future annotations.
- Logs con `logging` estándar, nunca `print()`.
- Secrets en `.env`, nunca hardcodeados. Acceder vía `get_settings()`.
- Validar entrada en la capa de router; lógica de negocio en services/.
- Errores: `HTTPException` en routers, `logger.exception()` antes de re-raise.

## Base de datos

- PostgreSQL con extensión PostGIS habilitada.
- ORM: SQLAlchemy 2.0 async con `mapped_column`.
- Migraciones: Alembic en modo async.
- Conexión: `asyncpg` como driver.

## Testing

- pytest + pytest-asyncio + httpx (AsyncClient).
- Fixtures en `tests/conftest.py`.
- Mocks para OpenAI y servicios externos.
