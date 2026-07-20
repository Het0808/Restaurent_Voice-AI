# Implementation Roadmap

## Delivery principles

Deliver one stage at a time, keep each stage runnable and tested, and do not introduce later integrations early. Each milestone ends with documentation updates, relevant Pytest coverage, Ruff and MyPy checks, and honest reporting of failures.

## Milestones

### Stage 0 — Project initialization (Completed)

Establish project objective, development rules and progress tracking.

### Stage 1 — Architecture and planning (Completed)

Define the modular architecture, request flows, data model, LangGraph state machine, API contracts, target folder structure, security, latency goals and staged plan. Deliver documentation only.

### Stage 2 — FastAPI foundation

Create Python 3.12 packaging, typed configuration, application factory/lifespan, health endpoints, structured logging, error envelopes and baseline test/quality configuration. No reservation, RAG, speech, LangGraph or Twilio implementation.

**Exit criteria:** app starts; liveness/readiness contracts and configuration tests pass; Ruff and MyPy are configured.

### Stage 3 — Reservation database

Add PostgreSQL, SQLAlchemy 2 models/repositories, Alembic migrations and reservation services for availability, create, find, modify and cancel. Enforce transactions, overlap protection, idempotency and audit events.

**Exit criteria:** migrations apply cleanly; integration tests cover success, conflict, concurrency and rollback; confirmation is derived only from committed results.

### Stage 4 — RAG pipeline

Add controlled document ingestion, chunking, ChromaDB vector retrieval, BM25 retrieval, rank merging, restaurant/language filters and citations. Keep availability outside RAG.

**Exit criteria:** fixture documents can be indexed/removed; retrieval tests demonstrate scoping, hybrid ranking and insufficient-evidence behavior.

### Stage 5 — LangGraph workflow

Implement typed state, bounded nodes/edges, OpenAI tool calling and narrow reservation/RAG tools. Add multilingual response rules, explicit write confirmation and failure/handoff routing.

**Exit criteria:** deterministic graph tests cover every intent, conditional edge, tool failure and the rule that database success precedes spoken confirmation.

### Stage 6 — Speech-to-text

Implement the STT protocol and selected provider adapter with supported audio conversion, partial/final transcript handling, language hints, timeouts and metrics.

**Exit criteria:** English, Hindi and Gujarati fixtures produce normalized transcript events; provider failure/cancellation tests pass.

### Stage 7 — Text-to-speech

Implement the TTS protocol and selected provider adapter with streaming output, language/voice selection, cancellation and pronunciation configuration.

**Exit criteria:** all supported languages generate playable output; first-audio latency and cancellation are measured and tested.

### Stage 8 — Browser voice demo

Add browser session REST setup, the real-time WebSocket protocol, audio/session coordination and a minimal browser client for end-to-end voice interaction.

**Exit criteria:** a local user can complete FAQ and reservation scenarios by voice; backpressure, reconnect/error and basic interruption behavior are tested.

### Stage 9 — Twilio integration

Add signature-validated Twilio Voice webhook and bidirectional Media Streams adapter, translating Twilio events to the existing internal protocol.

**Exit criteria:** a test call completes representative flows; signature, disconnect and media contract tests pass without changing core workflow logic.

### Stage 10 — Interruption and human handoff

Harden server/client VAD behavior, cancel STT/LLM/TTS work on barge-in, flush obsolete playback and implement transport-aware transfer/fallback.

**Exit criteria:** interruption latency is measured; repeated failure and explicit handoff scenarios have verified outcomes.

### Stage 11 — Evaluation and monitoring

Add multilingual scenario datasets, regression scoring, tool correctness checks, latency/error dashboards, tracing and privacy-safe operational alerts.

**Exit criteria:** quality and latency baselines exist with release thresholds; sensitive data is redacted from telemetry.

### Stage 12 — Deployment and documentation

Add Docker and Compose, production runtime configuration, migrations/deployment procedure, backup/recovery notes, operator runbooks and portfolio documentation.

**Exit criteria:** clean-environment deployment is reproducible; smoke tests, security checklist and user/operator guides are complete.

## MVP completion definition

Stages 0–10 produce the functional MVP: one restaurant, three languages, grounded FAQs, safe reservation lifecycle, browser and Twilio voice paths, interruption and handoff. Stages 11–12 make it measurable, deployable and portfolio-ready.

## Post-MVP improvements

Add multiple restaurants/locations, waitlists, table optimization, POS/CRM integrations, outbound notifications, provider failover, distributed Redis-backed session coordination, human-agent tooling, more languages and continuous evaluation from consented/redacted production signals.
