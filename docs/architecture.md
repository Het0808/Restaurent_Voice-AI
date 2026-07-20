# System Architecture

## Architectural approach

The MVP is a modular monolith: one deployable application with strict internal module boundaries. This keeps operations simple while allowing high-load or vendor-specific components to be extracted later. Browser and future Twilio transports use the same conversation workflow and business services.

## System context

```text
Browser client                         Twilio Voice (future)
      | HTTPS / WebSocket audio              | Media Stream
      +-------------------+-------------------+
                          v
                  Transport adapters
                          |
                Audio/session coordinator
                    |             |
                   STT           TTS
                    |             ^
                    v             |
                 LangGraph conversation workflow
                    |             |              |
             FAQ retrieval   Reservation tools  Handoff
                    |             |
          ChromaDB + BM25     Business service
                                  |
                              PostgreSQL
```

## Components and responsibilities

| Component | Responsibility | Must not do |
|---|---|---|
| REST adapter | Health, session setup, text demo, document administration, reservation management for authorized staff | Contain business rules |
| WebSocket adapter | Maintain a real-time client session and exchange audio/text/control events | Call the database directly |
| Twilio adapter (Stage 9) | Validate Twilio requests and translate Media Stream events to internal events | Own conversation logic |
| Session coordinator | Track connection lifecycle, buffering, turn boundaries, cancellation and backpressure | Decide reservation outcomes |
| STT adapter | Convert audio to timestamped transcripts and expose language confidence | Route intents or access data |
| Language service | Resolve English, Hindi or Gujarati and retain the caller's preference | Translate database values destructively |
| LangGraph workflow | Hold conversational state, select bounded actions and coordinate tools | Execute SQL or declare a write successful without a tool result |
| Reservation tools | Expose typed, narrow operations to the workflow | Accept SQL or bypass validation |
| Reservation service | Validate policies, check availability, execute atomic writes and return authoritative results | Use RAG for availability |
| FAQ retrieval | Ingest approved documents and perform ChromaDB vector plus BM25 lexical retrieval | Answer live availability questions |
| Response composer | Produce short, natural, language-matched responses grounded in tool/retrieval results | Invent business facts |
| TTS adapter | Synthesize streaming speech and support cancellation on interruption | Determine response content |
| Handoff service | Decide/record handoff requests and connect to a human transport when available | Silently discard failed conversations |
| PostgreSQL | Source of truth for restaurants, tables, customers and reservations | Store document embeddings |
| ChromaDB/BM25 index | Store searchable restaurant-document chunks | Store live reservation state |
| Redis (optional) | Ephemeral session/cache/rate-limit state where in-memory state is insufficient | Become the reservation source of truth |
| Observability | Structured logs, correlation IDs, latency metrics and redacted error reporting | Log secrets or raw sensitive audio by default |

## Complete request flows

### Voice turn

1. The client opens an authenticated WebSocket session and negotiates the supported audio format.
2. The transport adapter validates events and forwards audio frames to the session coordinator.
3. The coordinator sends buffered/streaming audio to STT and receives partial and final transcripts.
4. A language result is stored in conversation state; explicit caller preference overrides detection.
5. A final transcript enters the LangGraph workflow.
6. The workflow classifies the request and either retrieves FAQ context, gathers missing reservation fields, invokes one narrow reservation tool, or requests handoff.
7. FAQ answers are grounded only in retrieved approved documents. Availability and reservation results come only from the reservation service and PostgreSQL.
8. The response composer creates a concise response in the selected language. A reservation is described as confirmed only when the successful database result includes its identifier.
9. TTS streams audio to the coordinator, which emits it over the active transport.
10. If new caller speech arrives, the coordinator cancels outstanding synthesis/playback, records the interruption, and begins the next turn.

### Reservation write

1. The workflow gathers required fields and reads them back for explicit confirmation.
2. A typed create, modify or cancel tool validates its arguments.
3. The reservation service applies restaurant policy and opens a database transaction.
4. It locks/checks relevant availability, performs the mutation and commits atomically.
5. Only a committed success result is returned as confirmed. Conflict or failure returns a safe alternative/error result.
6. The workflow reports the authoritative result without exposing internal details.

### FAQ retrieval

1. Approved documents are normalized, chunked and indexed in ChromaDB and BM25 with restaurant and language metadata.
2. The query is searched lexically and semantically within the active restaurant.
3. Ranked results are merged, filtered by a relevance threshold and passed to response composition with source metadata.
4. With insufficient evidence, the assistant says it does not know and offers human help.

## Error handling and resilience

- Every request/connection receives a correlation ID; errors use stable public codes and redacted internal logs.
- Invalid client events receive a recoverable error event; repeated protocol violations close the socket.
- STT/TTS/LLM calls use bounded timeouts, limited retries with jitter for transient errors, and cancellation propagation.
- Database conflicts are expected domain outcomes, not generic server errors. Writes are transactional and create operations use idempotency keys.
- Retrieval failure produces an honest fallback rather than an ungrounded answer.
- Session failure preserves only the minimum safe recovery metadata and offers handoff when possible.
- Readiness fails when required dependencies are unavailable; liveness only reports process health.

## Security

- Store credentials only in environment-backed configuration; never commit secrets.
- Authenticate staff/admin endpoints and authorize by restaurant and role. Use short-lived session tokens for browser WebSockets.
- Validate Twilio signatures when that adapter is introduced; use TLS/WSS everywhere.
- Validate all input with bounded lengths, MIME/audio formats and typed schemas; never accept SQL from an LLM or client.
- Parameterize all database access through repositories and enforce least-privilege database roles.
- Encrypt data in transit and at rest, minimize PII, define retention/deletion policies, and redact phone numbers, transcripts and reservation details from logs.
- Require explicit controls for document ingestion and isolate retrieval by restaurant.
- Apply rate limits, connection limits, origin checks and payload size limits.
- Maintain auditable reservation status changes without storing secrets in audit metadata.

## Latency considerations

Target natural turn-taking rather than maximum model complexity. Stream audio, STT partials and TTS output; cancel obsolete work on interruption. Keep one long-lived WebSocket per call, reuse provider clients and database pools, and avoid synchronous work in the audio loop. Run FAQ retrieval and safe independent preparation concurrently where useful. Set and measure budgets for final STT, workflow/tool execution, first LLM token and first TTS audio byte. Cache only stable FAQ/index metadata, never unverified availability. Apply bounded queues and backpressure rather than allowing memory growth.

## MVP scope

- One restaurant configuration and timezone.
- English, Hindi and Gujarati voice/text turns.
- Approved FAQ documents with hybrid retrieval.
- Create, find, modify and cancel reservation workflows.
- Browser voice demo before Twilio integration.
- Basic interruption, human-handoff request, structured logs and core metrics.
- PostgreSQL as the authoritative reservation store.

Not in the initial MVP: payments, delivery ordering, loyalty programs, outbound campaigns, multi-location optimization, custom acoustic models, or autonomous policy changes.

## Future improvements

- Multi-tenant restaurant administration and per-location policies.
- Redis-backed distributed sessions, queues and rate limiting.
- Calendar/POS/CRM integrations and event-driven notifications.
- Advanced table optimization, waitlists and group reservations.
- Provider fallback, regional deployment and autoscaling of audio workers.
- Human-agent console, call summaries and consent-aware analytics.
- Expanded languages, pronunciation dictionaries and systematic quality evaluation.
