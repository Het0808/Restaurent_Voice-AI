# Multilingual AI Restaurant Voice Receptionist

A portfolio-grade backend for an AI voice receptionist designed to assist restaurant callers in English, Hindi, and Gujarati. The planned system will answer approved restaurant FAQs, manage reservations safely, and eventually support browser and Twilio voice calls.

## Current capabilities

Stage 2 provides the production-oriented FastAPI foundation:

- Application factory and modern lifespan handling
- Environment-backed Pydantic v2 settings
- Versioned API router
- Root and health endpoints with typed response models
- Central exception handling and safe error responses
- Readable structured request and lifecycle logging
- Configurable CORS allowlist
- Pytest, Ruff, and MyPy configuration

No database, reservation, RAG, AI, speech, telephony, Redis, authentication, or Docker functionality is implemented yet.

## Prerequisites

- macOS or another Unix-like environment
- Python 3.12

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

The defaults are suitable for local development and no secrets are required in Stage 2.

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
| `GET` | `/docs` | Interactive OpenAPI documentation |

## Current limitations

- Health checks cover only the application process because no external dependencies exist yet.
- CORS is configured for explicit development origins only.
- The service does not yet persist data or perform receptionist workflows.
- Authentication and production deployment configuration are intentionally deferred.

## Next stage

Stage 3 will add the PostgreSQL reservation database, SQLAlchemy 2 models, Alembic migrations, and tested reservation business operations. See [project context](docs/project-context.md), [architecture](docs/architecture.md), and [progress](docs/progress.md) for details.
