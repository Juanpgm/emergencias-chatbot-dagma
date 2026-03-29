# SKILLS — DAGMA Emergencias Bot

Directorio de habilidades especializadas para este proyecto. Cada skill contiene
instrucciones específicas para realizar una tarea con alta calidad.

## Skills disponibles

| Skill                | Archivo                                  | Descripción                                      |
| -------------------- | ---------------------------------------- | ------------------------------------------------ |
| FastAPI Routing      | `.claude/skills/fastapi-routing.md`      | Crear endpoints, manejar Form data, dependencias |
| LangChain Extraction | `.claude/skills/langchain-extraction.md` | Structured output con Pydantic + GPT-4o          |
| Database Ops         | `.claude/skills/database-ops.md`         | SQLAlchemy async, migraciones, PostGIS           |
| WhatsApp Integration | `.claude/skills/whatsapp-integration.md` | Webhook Twilio, procesamiento de mensajes        |
| Audio Processing     | `.claude/skills/audio-processing.md`     | Descarga, conversión y transcripción con Whisper |
| Testing              | `.claude/skills/testing.md`              | pytest-asyncio, mocks, fixtures                  |
| Context Compression  | `.claude/skills/context-compression.md`  | Técnicas para reducir uso de tokens              |

## Cómo usar

Claude carga skills automáticamente cuando el trabajo actual coincide con su dominio.
También puedes pedirlo explícitamente: "usa el skill de testing para crear tests".
