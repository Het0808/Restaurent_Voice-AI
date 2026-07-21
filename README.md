# Multilingual AI Restaurant Voice Receptionist

A portfolio-grade backend for an AI voice receptionist designed to assist restaurant callers in English, Hindi, and Gujarati. The planned system will answer approved restaurant FAQs, manage reservations safely, and eventually support browser and Twilio voice calls.

## Current capabilities

Stage 3 provides a production-oriented FastAPI and PostgreSQL reservation foundation:

- Application factory and modern lifespan handling
- Environment-backed Pydantic v2 settings
- Versioned API router
- Root and health endpoints with typed response models
- Central exception handling and safe error responses
- Readable structured request and lifecycle logging
- Configurable CORS allowlist
- Pytest, Ruff, and MyPy configuration
- Async SQLAlchemy 2 engine and request-scoped sessions
- Alembic-managed PostgreSQL schema for restaurant tables, reservations, and call sessions
- Table creation and listing
- Availability checks using database overlap queries
- Transactional reservation creation, retrieval, modification, and cancellation
- PostgreSQL row locking to serialize competing table assignments
- Database readiness endpoint and idempotent sample-table seed script

No RAG, AI, speech, telephony, Redis, authentication, or Docker functionality is implemented yet.

## Prerequisites

- macOS or another Unix-like environment
- Python 3.12
- PostgreSQL 15 or newer for local runtime and migration testing

Install PostgreSQL on macOS with Homebrew if needed:

```bash
brew install postgresql@16
brew services start postgresql@16
```

## Setup

From the repository root, create and activate a virtual environment on macOS:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

Install the application and development tools:

```bash
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

Optional local configuration:

```bash
cp .env.example .env
```

Create a local database and apply the schema:

```bash
createdb restaurant_voice_ai
alembic upgrade head
```

The development example connection is:

```text
postgresql+asyncpg://postgres:postgres@localhost:5432/restaurant_voice_ai
```

Set `DATABASE_URL` in your uncommitted `.env` to match your local PostgreSQL role and password. The checked-in value is documentation only and must not be reused as a production credential.

To create a reviewed migration after changing models:

```bash
alembic revision --autogenerate -m "describe schema change"
```

Seed the sample layout after migrating:

```bash
PYTHONPATH=src python scripts/seed_tables.py
```

The seed is idempotent and creates tables with capacities 2, 2, 4, 4, 6, and 8.

## Development server

```bash
./scripts/run_dev.sh
```

The script adds `src` to `PYTHONPATH` and starts Uvicorn with reload enabled. API documentation is available at `http://127.0.0.1:8000/docs`.

## Quality checks

```bash
python -m pytest
ruff check .
ruff format --check .
mypy src
```

To apply automatic formatting and safe lint fixes:

```bash
ruff format .
ruff check --fix .
```

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/` | Service links and identity |
| `GET` | `/health` | Unversioned process health |
| `GET` | `/api/v1/health` | Versioned process health |
| `GET` | `/api/v1/health/database` | PostgreSQL readiness (`SELECT 1`) |
| `POST` | `/api/v1/tables` | Create a restaurant table |
| `GET` | `/api/v1/tables` | List restaurant tables |
| `GET` | `/api/v1/tables/{table_id}` | Retrieve a restaurant table |
| `POST` | `/api/v1/reservations/availability` | Find suitable available tables |
| `POST` | `/api/v1/reservations` | Create a confirmed reservation transactionally |
| `GET` | `/api/v1/reservations` | List reservations |
| `GET` | `/api/v1/reservations/{reservation_id}` | Retrieve by UUID |
| `GET` | `/api/v1/reservations/code/{confirmation_code}` | Retrieve by confirmation code |
| `PATCH` | `/api/v1/reservations/{reservation_id}` | Modify a reservation |
| `POST` | `/api/v1/reservations/{reservation_id}/cancel` | Cancel without deleting |
| `GET` | `/docs` | Interactive OpenAPI documentation |

## API examples

Create a table:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/tables \
  -H 'Content-Type: application/json' \
  -d '{"table_number":1,"capacity":4,"area":"Window"}'
```

Check availability with timezone-aware timestamps:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/reservations/availability \
  -H 'Content-Type: application/json' \
  -d '{"party_size":4,"reservation_start":"2026-08-01T19:00:00+05:30","reservation_end":"2026-08-01T20:30:00+05:30"}'
```

Create a reservation:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/reservations \
  -H 'Content-Type: application/json' \
  -d '{"customer_name":"Asha Patel","customer_phone":"+919876543210","party_size":4,"reservation_start":"2026-08-01T19:00:00+05:30","language":"gu"}'
```

Cancel a reservation, replacing the UUID:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/reservations/00000000-0000-0000-0000-000000000000/cancel \
  -H 'Content-Type: application/json' \
  -d '{}'
```

## Current limitations

- Authentication and tenant isolation are not implemented; the API is for controlled development use.
- CORS is configured for explicit development origins only.
- The standard test suite uses temporary SQLite for portability. It does not prove PostgreSQL row-lock concurrency semantics.
- PostgreSQL `SELECT FOR UPDATE` protects application writes, but a database exclusion constraint is deferred.
- Reservation emails and phone numbers receive only basic length/blank validation in this stage.
- Call-session storage exists for future use, but no call handling is implemented.

## Next stage

Stage 4 will add the restaurant-document RAG pipeline while keeping live availability exclusively in PostgreSQL. See [project context](docs/project-context.md), [architecture](docs/architecture.md), and [progress](docs/progress.md) for details.
