# DAGMA Emergencias Bot 🌿

Backend inteligente para atención de emergencias ambientales vía WhatsApp, desarrollado para el **DAGMA** (Departamento Administrativo de Gestión del Medio Ambiente) de Cali, Colombia.

## Características

- **Recepción de mensajes** vía webhook de WhatsApp (Twilio)
- **Transcripción de voz** con OpenAI Whisper
- **Extracción inteligente** de datos con LangChain + GPT-4o
- **Clasificación automática** de tipo de emergencia y nivel de gravedad
- **Geolocalización** con PostGIS (coordenadas GPS o ubicación inferida)
- **Persistencia** en PostgreSQL

## Stack tecnológico

| Componente    | Tecnología             |
| ------------- | ---------------------- |
| Backend       | Python 3.11+ / FastAPI |
| Transcripción | OpenAI Whisper         |
| Extracción IA | LangChain + GPT-4o     |
| Base de datos | PostgreSQL + PostGIS   |
| ORM           | SQLAlchemy 2.0 (async) |
| Migraciones   | Alembic                |
| Driver DB     | asyncpg                |

## Estructura del proyecto

```
emergencias_dagma_chatbot/
├── app/
│   ├── main.py                 # Entry point FastAPI
│   ├── core/
│   │   ├── config.py           # Settings (pydantic-settings)
│   │   └── database.py         # Engine async PostgreSQL
│   ├── schemas/
│   │   └── emergencia.py       # Modelos Pydantic
│   ├── models/
│   │   └── emergencia.py       # ORM SQLAlchemy
│   ├── services/
│   │   ├── transcripcion.py    # Whisper: audio → texto
│   │   ├── extraccion.py       # LangChain: texto → datos estructurados
│   │   └── persistencia.py     # Guardar en PostgreSQL
│   └── routers/
│       └── whatsapp.py         # POST /webhook/whatsapp
├── alembic/                    # Migraciones de BD
├── tests/                      # Tests
├── .claude/                    # Config Claude Code
│   ├── rules/                  # Reglas por contexto
│   └── skills/                 # Skills especializados
├── CLAUDE.md                   # Instrucciones para Claude Code
├── TOOLS.md                    # Herramientas disponibles
├── SKILLS.md                   # Índice de skills
├── requirements.txt
└── .env.example
```

## Instalación

### 1. Clonar y configurar entorno

```bash
git clone <repo-url>
cd emergencias_dagma_chatbot
python -m venv .venv

# Windows
.venv\Scripts\Activate.ps1
# Linux/Mac
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tus API keys y conexión a PostgreSQL
```

### 3. Preparar PostgreSQL

```sql
CREATE DATABASE emergencias_dagma;
\c emergencias_dagma
CREATE EXTENSION IF NOT EXISTS postgis;
```

### 4. Ejecutar migraciones

```bash
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

### 5. Iniciar servidor

```bash
uvicorn app.main:app --reload --port 8000
```

## Uso

### Health check

```bash
curl http://localhost:8000/health
```

### Simular mensaje de texto

```bash
curl -X POST http://localhost:8000/webhook/whatsapp \
  -d "From=whatsapp:+573001234567" \
  -d "Body=Hay un incendio forestal en el cerro de las Tres Cruces, cerca del barrio San Antonio" \
  -d "NumMedia=0"
```

### Simular mensaje con ubicación

```bash
curl -X POST http://localhost:8000/webhook/whatsapp \
  -d "From=whatsapp:+573001234567" \
  -d "Body=Están talando árboles ilegalmente" \
  -d "NumMedia=0" \
  -d "Latitude=3.4516" \
  -d "Longitude=-76.5320"
```

## Datos extraídos automáticamente

El LLM analiza cada mensaje y extrae:

| Campo                         | Descripción                                            |
| ----------------------------- | ------------------------------------------------------ |
| `nombre_reportante`           | Nombre de quien reporta                                |
| `telefono`                    | Teléfono de contacto                                   |
| `email`                       | Correo electrónico                                     |
| `direccion_hechos`            | Dirección del incidente                                |
| `direccion_persona`           | Dirección del reportante                               |
| `tipo_de_emergencia`          | Categoría (incendio, tala ilegal, contaminación, etc.) |
| `descripcion_emergencia`      | Descripción del incidente                              |
| `descripcion_detallada`       | Resumen ampliado con contexto inferido                 |
| `ubicacion_inferida`          | Barrio, comuna o punto de referencia                   |
| `latitud` / `longitud`        | Coordenadas GPS                                        |
| `nivel_de_gravedad`           | alta / media / baja                                    |
| `requiere_atencion_inmediata` | true / false                                           |

## Licencia

Uso interno DAGMA — Todos los derechos reservados.
