# SKILL: FastAPI Routing para DAGMA

## Cuándo usar

Cuando necesites crear o modificar endpoints HTTP en este proyecto.

## Patrón estándar

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

router = APIRouter(prefix="/recurso", tags=["Recurso"])

@router.post("/", response_model=ResponseModel)
async def crear_recurso(
    campo: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    try:
        resultado = await servicio.procesar(campo)
        return ResponseModel(status="ok", data=resultado)
    except Exception:
        logger.exception("Error en crear_recurso")
        raise HTTPException(status_code=500, detail="Error interno")
```

## Checklist

- [ ] Router registrado en `app/main.py` con `app.include_router()`
- [ ] Modelo de respuesta Pydantic definido en `app/schemas/`
- [ ] Validación de entrada con Form() o Body()
- [ ] Manejo de errores con HTTPException
- [ ] Función async
- [ ] Logs antes del raise
