---
paths:
  - "app/models/**/*.py"
  - "app/core/database.py"
  - "alembic/**/*.py"
---

# Database Operations — Reglas

- SQLAlchemy 2.0 style: `DeclarativeBase`, `mapped_column`, `Mapped[T]`.
- Driver: `asyncpg` (nunca psycopg2 para conexiones async).
- Sesiones via `async_session_factory`, inyectadas con `Depends(get_db)`.
- PostGIS: usar `geoalchemy2.Geometry` para columnas espaciales; SRID=4326.
- Crear geometrías con `from_shape(Point(lon, lat), srid=4326)`.
- Migraciones: Alembic en modo async (`run_async_migrations`).
- Siempre `await db.commit()` + `await db.refresh(obj)` tras INSERT.
