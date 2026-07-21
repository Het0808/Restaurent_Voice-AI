# Multilingual AI Restaurant Voice Receptionist

A portfolio-grade backend for an AI voice receptionist designed to assist restaurant callers in English, Hindi, and Gujarati. The planned system will answer approved restaurant FAQs, manage reservations safely, and eventually support browser and Twilio voice calls.

## Current capabilities

Stage 4 adds restaurant knowledge retrieval to the FastAPI and PostgreSQL foundation:

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
- Markdown, text, and text-based PDF knowledge loaders
- Heading-aware deterministic chunks with stable IDs
- Provider-neutral embeddings with Google, OpenAI, and local implementations
- Persistent ChromaDB vectors and in-memory BM25 lexical search
- Weighted hybrid fusion, score breakdowns, and an optional reranking interface
- Retrieval-only context and chunk-derived citations
- Knowledge ingestion, upload, search, statistics, and deletion APIs

No final-answer LLM, LangGraph, speech, telephony, Redis, authentication, or Docker functionality is implemented yet.

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

Google is the default. Create a key in [Google AI Studio](https://aistudio.google.com/app/apikey), then configure:

```bash
EMBEDDING_PROVIDER=google
GOOGLE_API_KEY='your-key-from-a-secure-secret-store'
GOOGLE_EMBEDDING_MODEL=text-embedding-004
```

To use OpenAI instead:

```bash
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY='your-key-from-a-secure-secret-store'
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

For local development without an API key:

```bash
EMBEDDING_PROVIDER=local
LOCAL_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

The local model downloads automatically on first use and can run offline after it is cached. Never commit API keys. The API starts without a remote key; only embedding-dependent operations return a configuration error.

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

Ingest the fictional sample knowledge after configuring the selected provider:

```bash
PYTHONPATH=src python scripts/ingest_knowledge.py
```

## RAG architecture

Vector retrieval finds semantic matches and paraphrases; BM25 favors exact menu names, allergens, times, and policy terms. Each result list is normalized independently, then combined using the default score `0.6 × vector + 0.4 × BM25`. Stable chunk IDs remove duplicates before thresholding and top-K selection. A no-op reranker provides an extension point without adding a large local model.

Ingestion flows through validated loader → heading-aware chunker → selected embedding provider → source replacement in Chroma → BM25 rebuild. Queries use the same provider before Chroma and BM25 retrieval, normalized weighted fusion, thresholding, context, and citations. The RAG service depends only on the shared provider interface.

| RAG setting | Default |
|---|---|
| `EMBEDDING_PROVIDER` | `google` |
| `GOOGLE_EMBEDDING_MODEL` | `text-embedding-004` |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` |
| `LOCAL_EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` |
| `CHROMA_PERSIST_DIRECTORY` | `.chroma` |
| `CHROMA_COLLECTION_NAME` | `restaurant_knowledge` |
| `RAG_TOP_K` | `5` |
| `RAG_VECTOR_WEIGHT` / `RAG_BM25_WEIGHT` | `0.6` / `0.4` |
| `RAG_SCORE_THRESHOLD` | `0.15` |
| `RAG_CHUNK_SIZE` / `RAG_CHUNK_OVERLAP` | `800` / `120` characters |

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
| `POST` | `/api/v1/knowledge/search` | Retrieve ranked evidence and citations |
| `POST` | `/api/v1/knowledge/ingest/default` | Ingest `data/knowledge` |
| `POST` | `/api/v1/knowledge/upload` | Ingest one supported document |
| `GET` | `/api/v1/knowledge/stats` | Return Chroma and BM25 statistics |
| `DELETE` | `/api/v1/knowledge/source/{source_name}` | Delete one indexed source |
| `POST` | `/api/v1/conversation/message` | Process one stateless deterministic conversation turn |
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

Retrieve evidence:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/knowledge/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"Does paneer tikka contain dairy?","top_k":5}'
```

Expected evidence is sample menu or FAQ text stating that paneer and its yogurt marinade contain dairy. This is documentation retrieval, not medical advice or a guarantee that food is safe for an allergy.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/knowledge/ingest/default

curl -X POST http://127.0.0.1:8000/api/v1/knowledge/upload \
  -F 'file=@data/knowledge/menu.md'
```

Citations are emitted only for retrieved chunks, using markers such as `[Source: menu.md | Section: Main Course]`. No qualifying result produces empty context/citations and `evidence_found: false`.

## Current limitations

- Authentication and tenant isolation are not implemented; the API is for controlled development use.
- CORS is configured for explicit development origins only.
- The standard test suite uses temporary SQLite for portability. It does not prove PostgreSQL row-lock concurrency semantics.
- PostgreSQL `SELECT FOR UPDATE` protects application writes, but a database exclusion constraint is deferred.
- Reservation emails and phone numbers receive only basic length/blank validation in this stage.
- Call-session storage exists for future use, but no call handling is implemented.
- RAG stores approved static documents only; live availability remains in PostgreSQL.
- Remote providers require their matching key; local embeddings require no API key.
- Switching providers changes vector dimensions, so existing sources must be reingested into an empty or differently named Chroma collection.
- PDF loading extracts embedded text only and does not use OCR.
- BM25 is process-local and intentionally uses simple tokenization.
- Allergen evidence is informational and cannot guarantee an allergen-free meal.
- The Stage 5 conversation API is stateless and English-first for entity extraction; Hindi and Gujarati currently have bounded keyword intent support.

## Conversation workflow

The Stage 5 LangGraph workflow uses offline rules by default, delegates restaurant-document questions to RAG, and delegates live availability and reservation mutations to PostgreSQL-backed services. It has no autonomous loops and never places services or secrets in graph state.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/conversation/message \
  -H 'Content-Type: application/json' \
  -d '{"message":"Is a table available on 2030-08-01 at 7 PM for four?","language":"en"}'
```

Configuration defaults to `CONVERSATION_INTENT_PROVIDER=rules`. Optional Google classification and extraction require both `CONVERSATION_INTENT_PROVIDER=google`, `GOOGLE_API_KEY`, and `GOOGLE_CHAT_MODEL`; provider failures safely fall back to rules. See [conversation graph design](docs/conversation-graph.md).

## Next stage

Stage 6 will add the LLM response generation and tool layer while preserving the deterministic workflow and business-service boundaries. See [conversation graph design](docs/conversation-graph.md), [architecture](docs/architecture.md), and [progress](docs/progress.md).
