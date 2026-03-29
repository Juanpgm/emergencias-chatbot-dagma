# Herramientas disponibles — DAGMA Emergencias Bot

## Terminal

- **Shell**: PowerShell (Windows) — usar `;` para encadenar comandos.
- **Python**: 3.11+ — entorno virtual en `.venv/`.
- **Package manager**: pip con `requirements.txt`.

## Comandos frecuentes

| Acción              | Comando                                                                                                                 |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Crear venv          | `python -m venv .venv; .venv\Scripts\Activate.ps1`                                                                      |
| Instalar deps       | `pip install -r requirements.txt`                                                                                       |
| Ejecutar servidor   | `uvicorn app.main:app --reload --port 8000`                                                                             |
| Nueva migración     | `alembic revision --autogenerate -m "msg"`                                                                              |
| Aplicar migraciones | `alembic upgrade head`                                                                                                  |
| Revertir migración  | `alembic downgrade -1`                                                                                                  |
| Linter              | `ruff check app/`                                                                                                       |
| Formato             | `ruff format app/`                                                                                                      |
| Tests               | `pytest tests/ -v`                                                                                                      |
| Test específico     | `pytest tests/test_extraccion.py -v -k "test_nombre"`                                                                   |
| Health check        | `curl http://localhost:8000/health`                                                                                     |
| Webhook test        | `curl -X POST http://localhost:8000/webhook/whatsapp -d "From=whatsapp:+573001234567&Body=Hay un incendio en el cerro"` |

## APIs externas

- **OpenAI**: Whisper (audio→texto) + GPT-4o (extracción). API key en `.env`.
- **Twilio**: Webhook entrante para WhatsApp. No se hace llamada saliente directa.

## Base de datos

- PostgreSQL local con PostGIS.
- Crear DB: `CREATE DATABASE emergencias_dagma;`
- Habilitar PostGIS: `CREATE EXTENSION IF NOT EXISTS postgis;`
- Conexión async via `asyncpg`.

## Debugging

- Logs: `LOG_LEVEL=DEBUG` en `.env` para ver queries SQL y payloads.
- FastAPI docs: `http://localhost:8000/docs` (Swagger UI).
- Validar schema: `python -c "from app.schemas.emergencia import DatosEmergencia; print(DatosEmergencia.model_json_schema())"`.
