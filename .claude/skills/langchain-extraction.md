# SKILL: LangChain Structured Extraction con Groq

## Cuándo usar

Cuando trabajes con la extracción de datos estructurados de texto de emergencias.

## Pipeline

```
texto usuario → ChatGroq (llama-3.3-70b) → .with_structured_output() → PydanticModel
```

## Código clave

```python
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0, api_key=settings.groq_api_key)

prompt = ChatPromptTemplate.from_messages([
    ("system", "Tu rol y reglas de extracción aquí..."),
    ("human", "Texto a analizar:\n\n{texto}"),
])

chain = prompt | llm.with_structured_output(MiModeloPydantic)

resultado = await chain.ainvoke({"texto": texto_del_usuario})
# resultado ya es una instancia de MiModeloPydantic
```

## Tips

- `with_structured_output()` usa function calling de Groq internamente.
- Los `Field(description=...)` en Pydantic guían al LLM sobre qué extraer.
- Temperature=0 para resultados consistentes.
- No necesitas parsear JSON — el chain retorna el objeto Pydantic directamente.
- Siempre usar `ainvoke()` (async) en FastAPI.
- Código canónico en `shared/services/extraccion.py`.

## Errores comunes

- Olvidar `await` en `ainvoke()`.
- Usar `ChatOpenAI` o `openai_api_key` — este proyecto usa Groq.
- No definir `description` en los Fields — el LLM no sabrá qué extraer.
