# Planned Folder Structure

No application folders or source files are created in Stage 1. The following is the target structure to introduce incrementally in later stages.

```text
.
├── AGENTS.md
├── README.md
├── .env.example
├── pyproject.toml
├── alembic.ini
├── docker-compose.yml
├── docs/
│   ├── project-context.md
│   ├── progress.md
│   ├── architecture.md
│   ├── database-design.md
│   ├── langgraph-design.md
│   ├── api-design.md
│   ├── folder-structure.md
│   └── implementation-roadmap.md
├── src/restaurant_voice/
│   ├── main.py
│   ├── config.py
│   ├── observability/
│   │   ├── logging.py
│   │   └── metrics.py
│   ├── api/
│   │   ├── dependencies.py
│   │   ├── errors.py
│   │   └── routes/
│   │       ├── health.py
│   │       ├── sessions.py
│   │       ├── reservations.py
│   │       └── documents.py
│   ├── transport/
│   │   ├── websocket.py
│   │   ├── browser.py
│   │   └── twilio.py
│   ├── audio/
│   │   ├── formats.py
│   │   ├── buffering.py
│   │   └── session.py
│   ├── stt/
│   │   ├── protocols.py
│   │   └── openai.py
│   ├── tts/
│   │   ├── protocols.py
│   │   ├── openai.py
│   │   └── elevenlabs.py
│   ├── conversation/
│   │   ├── state.py
│   │   ├── graph.py
│   │   ├── nodes.py
│   │   ├── edges.py
│   │   └── prompts.py
│   ├── rag/
│   │   ├── ingestion.py
│   │   ├── chunking.py
│   │   ├── vector_store.py
│   │   ├── bm25.py
│   │   └── retrieval.py
│   ├── reservations/
│   │   ├── schemas.py
│   │   ├── service.py
│   │   ├── repository.py
│   │   └── tools.py
│   ├── database/
│   │   ├── session.py
│   │   └── models.py
│   └── handoff/
│       ├── protocols.py
│       └── service.py
├── migrations/
│   ├── env.py
│   └── versions/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   └── fixtures/
└── scripts/
    ├── ingest_documents.py
    └── evaluate_conversations.py
```

## Boundary rules

- `api` and `transport` translate external protocols; they call services/workflows rather than repositories.
- `audio`, `stt` and `tts` own media concerns and provider adapters independently.
- `conversation` coordinates state and calls typed tools; it never imports database models or executes SQL.
- `reservations` owns business validation and orchestrates persistence through its repository.
- `database` owns SQLAlchemy infrastructure and models, not reservation policy.
- `rag` owns document ingestion and retrieval; it cannot answer live availability.
- `handoff` exposes a transport-neutral contract that browser and Twilio adapters can implement.
- Tests mirror boundaries: unit tests for pure rules, integration tests for PostgreSQL/retrieval, and contract tests for provider/transport schemas.
- Provider modules implement internal protocols so vendors can be replaced without rewriting business logic.
