---
paths:
  - "shared/models/**/*.py"
  - "shared/core/database.py"
  - "alembic/**/*.py"
---

# Database Operations — Reglas

- SQLAlchemy 2.0 style: `DeclarativeBase`, `mapped_column`, `Mapped[T]`.
- Driver async: `asyncpg` (nunca psycopg2 para conexiones async).
- Driver sync: `psycopg2-binary` — solo Alembic usa psycopg2.
- Sesiones via `async_session_factory`, inyectadas con `Depends(get_db)`.
- Sin PostGIS — no usar `geoalchemy2` ni columnas `Geometry`.
- Alembic: modo **síncrono** — `env.py` usa `engine_from_config` + `psycopg2`, no `run_async_migrations`.
- SSL: `sslmode="disable"` en development, `sslmode="require"` en otros entornos.
- Relaciones con tablas especializadas: siempre `cascade="all, delete-orphan", passive_deletes=True`.
- Siempre `await db.commit()` + `await db.refresh(obj)` tras INSERT.
