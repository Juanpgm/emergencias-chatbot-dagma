---
paths:
  - "app/routers/**/*.py"
---

# FastAPI Routing — Reglas

- Cada router en un archivo separado bajo `app/routers/`.
- Prefijo de URL obligatorio en `APIRouter(prefix="/...")`.
- Usar `Depends(get_db)` para inyectar sesión de DB.
- Validar entrada con Form() o Body(); nunca confiar en datos crudos.
- Retornar modelos Pydantic, no dicts.
- Manejar errores con HTTPException; loguear con logger.exception() antes.
- Funciones async para todo handler que haga I/O.
