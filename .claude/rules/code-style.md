# Estilo de código — Reglas globales

- `from __future__ import annotations` en la primera línea de cada módulo.
- Tipo unions con `X | None` en vez de `Optional[X]`.
- Line length máximo: 100 caracteres.
- Imports ordenados: stdlib → third-party → local (ruff se encarga).
- Funciones async para cualquier operación de I/O.
- Logging con `logger = logging.getLogger(__name__)`, nunca `print()`.
- f-strings para interpolación; no `.format()` ni `%`.
- Docstrings en español con formato breve (una línea o imperativo + descripción).
