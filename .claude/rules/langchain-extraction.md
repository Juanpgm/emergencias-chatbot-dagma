---
paths:
  - "shared/services/extraccion.py"
  - "shared/schemas/**/*.py"
---

# LangChain Extraction — Reglas

- Usar `ChatGroq` (langchain-groq), NO ChatOpenAI.
- Modelo: `llama-3.3-70b-versatile`. API key: `settings.groq_api_key`.
- Usar `.with_structured_output(PydanticModel)` para salida tipada.
- Prompts en español; sistema define rol del DAGMA y reglas de clasificación.
- Temperature 0 para resultados determinísticos.
- Chain: `prompt | llm.with_structured_output(Model)`.
- Invocar con `await chain.ainvoke()` (async).
- No parsear JSON manualmente; LangChain + Pydantic lo validan.
- Modelo Pydantic con `Field(description=...)` para guiar la extracción.
- Código canónico en `shared/services/extraccion.py`; los routers de app/ y chatbot/ usan shims.
