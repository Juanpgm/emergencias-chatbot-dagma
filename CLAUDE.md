# DAGMA Emergencias Bot — Instrucciones para Claude Code

## Autonomía

- Ejecutar comandos, crear archivos, editar código y correr tests SIN pedir permiso.
- Solo preguntar antes de: eliminar archivos/ramas, git push, modificar `.env`, operaciones destructivas en DB.
- Instalar dependencias, correr migraciones, formatear código → ejecutar directamente.
- No preguntar "¿quieres que haga X?" — hacerlo.

## Proyecto

Backend **solo API** (sin interfaz gráfica) para atención de emergencias ambientales vía WhatsApp (DAGMA, Cali).

- **No crear** frontend, templates HTML, UI web ni CLI interactivo.
- Los puntos de entrada son los webhooks de WhatsApp (app/ para Twilio legacy, chatbot/ para Meta Cloud API).

## Stack

- Python 3.11+ / FastAPI / Uvicorn
- **Groq** `whisper-large-v3-turbo` (transcripción de voz) — NO OpenAI Whisper
- **LangChain + ChatGroq** `llama-3.3-70b-versatile` (extracción estructurada) — NO GPT-4o
- PostgreSQL / SQLAlchemy 2.0 async / Alembic — **sin PostGIS**
- Redis (chatbot/ únicamente — estado de conversación con TTL 1800s)
- Pydantic v2 para validación
- JWT (HS256) + bcrypt para auth del panel admin

## Estructura del monorepo

PYTHONPATH root = `back/`. Hay 3 servicios FastAPI + un paquete `shared/`:

```
back/
├── shared/                 # Paquete canónico compartido
│   ├── core/
│   │   ├── config.py       # Settings (pydantic-settings) — incluye redis_url
│   │   └── database.py     # Engine async + session factory (asyncpg)
│   ├── models/
│   │   └── emergencia.py   # ORM SQLAlchemy — ReporteEmergencia, AdminUser, etc.
│   ├── schemas/
│   │   ├── emergencia.py   # Enums + schemas de entrada del bot
│   │   └── admin.py        # EstadoEmergencia (canónico), DTOs admin, TRANSICIONES_ESTADO
│   └── services/
│       ├── extraccion.py   # LangChain+Groq: texto → DatosEmergencia
│       ├── persistencia.py # Guarda reportes en DB
│       └── transcripcion.py # Groq Whisper: descarga + transcribe audio (límite 25 MB)
│
├── app/                    # Bot Twilio (LEGACY — a retirar)
│   └── ...                 # routers, services son shims → shared/
│
├── chatbot/                # Bot Meta Cloud API (FUTURO — el servicio canónico)
│   ├── app/
│   │   ├── main.py         # FastAPI entry point — port 8081
│   │   ├── core/redis.py   # Redis async (aioredis), graceful degradation stateless
│   │   ├── routers/whatsapp.py
│   │   └── services/       # Shims → shared/services/
│   └── ...
│
├── admin/                  # Panel de gestión — port 8082
│   └── app/
│       ├── main.py
│       ├── core/auth.py    # JWT HS256 — access (30 min) + refresh (7 días)
│       └── routers/
│           ├── auth.py     # Login bcrypt + bootstrap primer admin
│           ├── profile.py  # Perfil + reset de contraseña
│           ├── reportes.py # Listado con paginación cursor
│           └── gestion.py  # Cambio de estado, asignación, seguimiento, historial
│
├── alembic/                # Migraciones (sync psycopg2, no async)
├── tests/
│   ├── admin/              # Suite canónica del panel admin
│   ├── chatbot/            # Suite del bot Meta
│   └── conftest.py
└── pyproject.toml          # Fuente única de configuración de herramientas
```

## Estados de emergencia (canónicos)

```
informada (inicial) → asignada → en_proceso → resuelta → cerrada
cancelada = terminal, alcanzable desde cualquier estado no-terminal
```

Ver `shared/schemas/admin.py` para `EstadoEmergencia` y `TRANSICIONES_ESTADO`.

## Comandos

- Instalar deps: `pip install -r requirements.txt`
- Ejecutar chatbot dev: `uvicorn chatbot.app.main:app --reload --port 8081`
- Ejecutar admin dev: `uvicorn admin.app.main:app --reload --port 8082`
- Infra local: `docker compose up -d` (Postgres + Redis)
- Migración nueva (datos): `alembic revision -m "descripcion"` (sin --autogenerate para migraciones de datos)
- Migración nueva (esquema): `alembic revision --autogenerate -m "descripcion"`
- Aplicar migraciones: `alembic upgrade head`
- Tests: `GROQ_API_KEY=test-key-for-tests pytest tests/ -v`

## Convenciones

- Código, comentarios y docstrings en español.
- Funciones async para I/O (DB, HTTP, APIs).
- Separar routers/, services/, schemas/, models/ por servicio.
- `from __future__ import annotations` en todos los módulos.
- Tipos explícitos; `Optional[X]` → `X | None` con future annotations.
- Logs con `logging` estándar, nunca `print()`.
- Secrets en `.env`, nunca hardcodeados. Acceder vía `get_settings()`.
- Validar entrada en la capa de router; lógica de negocio en services/.
- Errores: `HTTPException` en routers, `logger.exception()` antes de re-raise.

## Base de datos

- PostgreSQL (sin PostGIS) — ORM: SQLAlchemy 2.0 async con `mapped_column`.
- Driver async: `asyncpg`. Driver sync para Alembic: `psycopg2-binary`.
- Migraciones: Alembic en modo **síncrono** (env.py usa `engine_from_config` con `psycopg2`).
- SSL: deshabilitado en development, requerido en otros entornos.
- Pool: `pool_pre_ping=True`, `pool_recycle=3600`.
- Siempre `await db.commit()` + `await db.refresh(obj)` tras INSERT.

## Testing

- pytest + pytest-asyncio + httpx (AsyncClient).
- Fixtures en `tests/conftest.py` y `tests/<servicio>/conftest.py`.
- Mocks para Groq, Redis y servicios externos — sin hits a servicios reales.
- Variable de entorno necesaria: `GROQ_API_KEY=test-key-for-tests`.
