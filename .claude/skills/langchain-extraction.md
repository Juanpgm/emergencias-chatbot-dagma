# SKILL: LangChain Structured Extraction

## Cuándo usar

Cuando necesites extraer datos estructurados de texto libre usando LLM.

## Patrón con Pydantic structured output

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=settings.openai_api_key)

prompt = ChatPromptTemplate.from_messages([
    ("system", "Tu rol y reglas de extracción aquí..."),
    ("human", "Texto a analizar:\n\n{texto}"),
])

chain = prompt | llm.with_structured_output(MiModeloPydantic)

resultado = await chain.ainvoke({"texto": texto_del_usuario})
# resultado ya es una instancia de MiModeloPydantic
```

## Tips

- `with_structured_output()` usa function calling de OpenAI internamente.
- Los `Field(description=...)` en Pydantic guían al LLM sobre qué extraer.
- Temperature=0 para resultados consistentes.
- No necesitas parsear JSON — el chain retorna el objeto Pydantic directamente.
- Siempre usar `ainvoke()` (async) en FastAPI.

## Errores comunes

- Olvidar `await` en `ainvoke()`.
- Poner la API key directamente en el código (usar settings).
- No definir `description` en los Fields — el LLM no sabrá qué extraer.
