# SKILL: Database Operations con SQLAlchemy Async + PostGIS

## Cuándo usar

Cuando necesites crear modelos, queries o migraciones.

## Modelo ORM estándar

```python
from sqlalchemy import String, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class MiModelo(Base):
    __tablename__ = "mi_tabla"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(255))
```

## PostGIS

```python
from geoalchemy2 import Geometry
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

# En modelo:
geom = mapped_column(Geometry("POINT", srid=4326), nullable=True)

# Al insertar:
geom_value = from_shape(Point(longitude, latitude), srid=4326)
```

## Queries async

```python
from sqlalchemy import select

async def get_by_id(db: AsyncSession, id: int):
    result = await db.execute(select(MiModelo).where(MiModelo.id == id))
    return result.scalar_one_or_none()
```

## Migraciones

```bash
alembic revision --autogenerate -m "add tabla X"
alembic upgrade head
alembic downgrade -1
```
