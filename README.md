# Multilingual AI Restaurant Voice Receptionist

A portfolio-grade backend for an AI voice receptionist designed to assist restaurant callers in English, Hindi, and Gujarati. The planned system will answer approved restaurant FAQs, manage reservations safely, and eventually support browser and Twilio voice calls.

## Current capabilities

Stage 8C adds signed Twilio incoming-call webhooks using Twilio `<Gather>` speech recognition. Each call is mapped to the existing Redis-backed conversation memory, LangGraph workflow, deterministic reservation tools, PostgreSQL audit history, and call-session lifecycle record. Reservation writes still require explicit confirmation inside the existing conversation workflow.

Stage 7 adds a browser-compatible, real-time voice transport while keeping the Stage 6 conversation workflow as the only orchestration authority:

- `WS /api/v1/voice/ws` protocol `1.0` with JSON controls and binary PCM frames
- English (India), Hindi (India), and Gujarati (India) session languages
- Bounded PCM validation, pre-speech buffering, energy VAD, silence/explicit commits
- Stable multi-turn conversation IDs and Stage 6 confirmation/tool protections
- Fake offline STT/TTS defaults and lazy optional Google Cloud providers
- Chunked 24 kHz PCM playback, interruption, timeout, and cleanup behavior
- Dependency-free browser demo at `http://127.0.0.1:8000/voice-demo/`
- Safe voice status at `GET /api/v1/voice/status`

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
python -m pip install -e '.[local-embeddings]'
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
| `WS` | `/api/v1/voice/ws` | Real-time browser PCM voice session |
| `GET` | `/api/v1/voice/status` | Safe voice provider/session status |
| `POST` | `/api/v1/voice/incoming` | Validate an incoming Twilio call and return welcome TwiML |
| `POST` | `/api/v1/voice/process-speech` | Validate speech results, run LangGraph, and return response TwiML |
| `POST` | `/api/v1/voice/status` | Idempotently persist Twilio call lifecycle callbacks |
| `GET` | `/voice-demo/` | Minimal browser microphone demo |
| `GET` | `/docs` | Interactive OpenAPI documentation |

## Twilio incoming-call architecture

```mermaid
sequenceDiagram
    participant Caller
    participant Twilio
    participant API as FastAPI
    participant Graph as LangGraph
    participant Gemini
    participant Reservations as Reservation service
    participant State as PostgreSQL / Redis
    Caller->>Twilio: Incoming phone call
    Twilio->>API: Signed POST /voice/incoming
    API->>State: Create or load call session
    API-->>Twilio: TwiML Gather and welcome
    Twilio->>API: Signed SpeechResult
    API->>Graph: Conversation turn
    Graph->>Gemini: Structured interpretation/response
    Graph->>Reservations: Allowlisted validated tool
    Reservations->>State: Transaction or retrieval
    Graph-->>API: Structured concise response
    API-->>Twilio: TwiML Say and Gather/Dial/Hangup
    Twilio-->>Caller: Spoken response
```

Twilio performs speech collection for this webhook flow. The browser WebSocket STT/TTS pipeline remains separate. Gemini is optional at runtime: `hybrid` mode uses the deterministic fallback when Gemini is unavailable. No Twilio or Gemini test uses paid network calls.

### Twilio configuration

Set these values in the uncommitted `.env`:

```bash
PUBLIC_BASE_URL=https://your-public-tunnel.example
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1...
TWILIO_STAFF_PHONE_NUMBER=+1...
TWILIO_VALIDATE_SIGNATURES=true
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash
CONVERSATION_MEMORY_BACKEND=redis
IDEMPOTENCY_BACKEND=redis
REDIS_ENABLED=true
```

In the Twilio number console configure:

- Incoming call webhook: `POST {PUBLIC_BASE_URL}/api/v1/voice/incoming`
- Status callback: `POST {PUBLIC_BASE_URL}/api/v1/voice/status`

The exact public URL is part of Twilio signature verification, so `PUBLIC_BASE_URL` must exactly match the externally visible HTTPS scheme and host.

Expose a local server with either:

```bash
ngrok http 8000
cloudflared tunnel --url http://localhost:8000
```

Never disable signature validation outside development or tests. Do not log raw caller numbers, auth tokens, request headers, or unfiltered Twilio error payloads.

### Example call

Caller: “I would like a table for four tomorrow at eight.”

Receptionist: “May I have the name and phone number for the reservation?”

After collecting the missing fields, the receptionist summarizes the request and asks for confirmation. Only an explicit confirmation invokes the deterministic reservation tool; TwiML then speaks the committed result.

### Twilio troubleshooting

- `403`: `PUBLIC_BASE_URL`, auth token, or Twilio signature does not match.
- Repeated prompts: speech was empty or below `TWILIO_MIN_SPEECH_CONFIDENCE`.
- Staff transfer ends the call: configure `TWILIO_STAFF_PHONE_NUMBER`.
- Conversation fallback: verify `GEMINI_API_KEY`, `GEMINI_MODEL`, and RAG/Chroma permissions.

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

## Stage 7 voice setup

Offline fake providers are the default:

```env
VOICE_ENABLED=true
VOICE_STT_PROVIDER=fake
VOICE_TTS_PROVIDER=fake
VOICE_DEFAULT_LANGUAGE=en-IN
```

Input is raw signed 16-bit little-endian, mono, 16 kHz PCM. Output is raw mono 24 kHz PCM. The supported languages are `en-IN`, `hi-IN`, and `gu-IN`. Start the application and open `/voice-demo/`, or run the deterministic verifier:

```bash
python scripts/test_voice_websocket.py
```

For optional Google Cloud completed-utterance STT and TTS:

```bash
pip install -e '.[voice-google]'
```

```env
VOICE_STT_PROVIDER=google_cloud
VOICE_TTS_PROVIDER=google_cloud
GOOGLE_CLOUD_PROJECT=your-project-id
```

Google Cloud uses Application Default Credentials. Do not put credentials in browser code or commit credential files. Browser resampling and energy VAD are deliberately lightweight development implementations; sessions are process-local, Google partial transcripts are not emitted, WebM decoding is only an extension boundary, and telephony is not implemented. See [Stage 7 voice pipeline](docs/stage-7-voice-pipeline.md).

Verification commands:

```bash
pytest
ruff check .
ruff format --check .
mypy src
python scripts/test_multiturn_conversation.py
python scripts/test_voice_websocket.py
```

## Stage 8A production foundation

Development keeps authentication optional and uses in-memory coordination. Production validation requires API authentication, JSON logs, PostgreSQL, explicit hosts/origins, non-fake voice providers, and Redis whenever a Redis backend is selected.

Apply migrations and start locally:

```bash
alembic upgrade head
./scripts/run_dev.sh
```

Authenticated examples use placeholders only:

```bash
curl http://127.0.0.1:8000/health/live

curl -H "X-API-Key: <ADMIN_API_KEY>" http://127.0.0.1:8000/health/ready

curl -X POST http://127.0.0.1:8000/api/v1/conversation/message \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <CLIENT_API_KEY>" \
  -H "X-Request-ID: demo-request-001" \
  -d '{"message":"Does paneer tikka contain dairy?"}'

curl -H "X-API-Key: <ADMIN_API_KEY>" http://127.0.0.1:8000/metrics
```

Run the development deployment stack:

```bash
docker compose -f deploy/docker-compose.yml up --build
```

The Compose password is development-only. Replace credentials and configure `API_KEYS`, `ADMIN_API_KEYS`, trusted hosts, explicit origins, and TLS termination for any deployed environment. Redis backends are selected independently:

```env
REDIS_ENABLED=true
CONVERSATION_MEMORY_BACKEND=redis
IDEMPOTENCY_BACKEND=redis
RATE_LIMIT_BACKEND=redis
```

Operational verification:

```bash
pytest -m "not integration"
pytest -m integration
python scripts/verify_production_config.py
python scripts/test_production_stack.py
```

Optional load helpers:

```bash
pip install -e '.[load]'
locust -f scripts/load_test_text.py
python scripts/load_test_voice.py
```

Request IDs are validated and returned in `X-Request-ID`. Logs are JSON in production and redact phone-like text and credential-bearing URLs. Metrics use bounded labels and require admin access when authentication is enabled. Audit history stores masked transcripts and never raw audio. See [Stage 8A production readiness](docs/stage-8a-production-readiness.md).

Stage 8B will add telephony as a separate transport adapter without duplicating conversation, reservation, RAG, voice, or tool logic. No Twilio, SIP, or phone-call implementation is included in Stage 8A.
