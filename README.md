# Kira

Agente de negocio construido con [Strands Agents](https://strandsagents.com/): responde preguntas frecuentes, cotiza servicios y productos, consulta disponibilidad y agenda citas, eventos y pedidos.

## Arquitectura

```
kira/
  config.py                 # Settings desde .env
  time_utils.py             # Fechas y zona horaria
  money.py                  # Centavos, IVA y formato COP
  errors.py                 # Errores de negocio con códigos
  db/
    schema_business.sql     # db_1: catálogo, FAQ, cotizaciones, agenda, pedidos
    schema_sessions.sql     # db_2: sesiones Strands + memoria
    migrate.py              # Creación idempotente + seed
    seed.py                 # Datos demo
    business_repo.py        # Repositorio de negocio y motor de disponibilidad
    session_repository.py   # SessionRepository SQLite para Strands
    memory_store.py         # MemoryStore SQLite por cliente/sesión
  tools/                    # Tools organizadas por dominio
    faq.py
    catalog.py
    quotes.py
    availability.py
    bookings.py
    orders.py
  agent/
    prompts.py
    kira.py                 # build_agent()
  api/
    app.py                  # FastAPI
  cli.py                    # init-db, seed, ask, chat, serve
```

Dos bases SQLite separadas:

- `data/db_1_business.sqlite3`: datos del negocio.
- `data/db_2_sessions.sqlite3`: historial de conversaciones y memoria de largo plazo.

## Requisitos

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Docker (opcional)

## Configuración

```bash
uv sync
cp .env.example .env
```

Edita `.env` y define al menos:

```env
PROVEEDOR_MODELO=openrouter
OPEN_ROUTER_API_KEY=tu_api_key
OPEN_ROUTER_MODEL=openai/gpt-4o-mini
```

Proveedores soportados: `openrouter` (default), `openai_compatible`, `bedrock`, `ollama`, `gemini`.

## Uso

```bash
# Crear bases y sembrar datos demo
uv run python main.py init-db

# Conversación interactiva
uv run python main.py chat

# Un solo mensaje
uv run python main.py ask "¿Cuál es el horario de atención?"

# API HTTP
uv run python main.py serve
# http://localhost:8000/docs
```

## API

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Estado de las dos bases |
| GET | `/faq?query=horario` | Búsqueda en FAQ |
| GET | `/catalog?category=Cortes` | Catálogo de servicios y productos |
| GET | `/bookings?date=2026-11-12` | Reservas del día |
| GET | `/quotes/{folio}` | Cotización por folio |
| POST | `/chat` | Mensaje al agente |

Ejemplo:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Quiero una cita para corte clásico mañana","session_id":"demo-1"}'
```

## Tools del agente

- `faq_search`
- `list_catalog`
- `create_quote`, `get_quote`
- `check_availability`
- `book_appointment`, `book_event`
- `get_booking`, `cancel_booking`, `reschedule_booking`
- `create_order`
- `search_memory`, `add_memory` (las aporta `MemoryManager`)

## Pruebas

```bash
uv run pytest -q
```

Las pruebas usan bases temporales y no requieren API key.

## Docker

```bash
cp .env.example .env
# edita .env
docker compose up --build
```

Los datos persisten en el volumen `kira_data`. Si usas Ollama en el host, configura `OLLAMA_HOST=http://host.docker.internal:11434`.

## Notas

- Es una demo de un solo negocio; no incluye autenticación ni multi-tenant.
- Los precios se guardan en centavos y el IVA es configurable en `settings.tax_rate`.
- La política de cancelación se configura en `settings.cancellation_hours`.
- Para producción, añade autenticación, límites de tasa y un proveedor de secretos.
