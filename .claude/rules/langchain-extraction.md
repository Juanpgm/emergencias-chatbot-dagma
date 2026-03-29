---
paths:
  - "app/services/extraccion.py"
  - "app/schemas/**/*.py"
---

# LangChain Extraction — Reglas

- Usar `ChatOpenAI.with_structured_output(PydanticModel)` para salida tipada.
- Prompts en español; sistema define rol del DAGMA y reglas de clasificación.
- Temperature 0 para resultados determinísticos.
- Chain: `prompt | llm.with_structured_output(Model)`.
- Invocar con `await chain.ainvoke()` (async).
- No parsear JSON manualmente; LangChain + Pydantic lo validan.
- Modelo Pydantic con `Field(description=...)` para guiar la extracción.
