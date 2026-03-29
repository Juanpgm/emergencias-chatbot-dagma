---
paths:
  - "tests/**/*.py"
---

# Testing — Reglas

- Framework: pytest + pytest-asyncio.
- Client: `httpx.AsyncClient` con `ASGITransport(app=app)`.
- Fixtures en `tests/conftest.py`: app, client, db session override.
- Mockear servicios externos (OpenAI, Whisper) con `unittest.mock.patch`.
- Cada test es independiente; usar transacciones que se revierten.
- Naming: `test_<accion>_<escenario>` (ej. `test_webhook_texto_valido`).
- Assertions con valores concretos, no solo `assert response.status_code == 200`.
