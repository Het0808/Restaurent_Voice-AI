# API Design

## Conventions

The planned API uses `/api/v1`, JSON over HTTPS for REST and WSS for real-time sessions. Pydantic v2 schemas will reject unknown/invalid fields where appropriate. Times use RFC 3339 with an offset; phone numbers use E.164; identifiers are UUIDs. Responses include `X-Request-ID`. This document is a contract only—no API is implemented in Stage 1.

## REST APIs

| Method and path | Purpose | Access |
|---|---|---|
| `GET /health/live` | Process liveness | Platform |
| `GET /health/ready` | Required dependency readiness | Platform |
| `POST /api/v1/voice-sessions` | Create a short-lived browser voice/text session and WebSocket token | Public with rate limits / configured access |
| `POST /api/v1/conversations/turns` | Text-only demo turn through the same workflow | Session token |
| `GET /api/v1/reservations/{id}` | Retrieve one reservation after ownership/role verification | Customer session or staff |
| `GET /api/v1/reservations` | Staff search by bounded date, phone and status filters | Staff |
| `POST /api/v1/reservations` | Create via validated business service | Staff/client workflow; idempotency required |
| `PATCH /api/v1/reservations/{id}` | Modify allowlisted fields using version precondition | Staff/client workflow; idempotency required |
| `POST /api/v1/reservations/{id}/cancel` | Idempotent cancellation | Staff/client workflow; idempotency required |
| `POST /api/v1/documents` | Register an approved restaurant document for indexing | Admin |
| `GET /api/v1/documents` | List document/index status | Admin |
| `DELETE /api/v1/documents/{id}` | Remove a document from retrieval indexes | Admin |

Customer-facing reservation mutations normally occur as internal tools during a conversation; REST mutation routes reuse exactly the same application service and validation rules. No endpoint accepts SQL, arbitrary tool names or arbitrary database filters.

### Representative contracts

`POST /api/v1/voice-sessions` request includes `restaurant_id`, optional `preferred_language`, client capabilities and audio format. Response includes `session_id`, expiring `websocket_url`, token expiry and negotiated formats.

Reservation create fields include customer name, E.164 phone, timezone-aware start, party size, optional duration, language and special requests. The `Idempotency-Key` header is required. Successful creation returns `201`; replay returns the same semantic result.

Reservation modification includes `expected_version` and only changed fields. A stale version or lost availability returns `409` with a safe conflict code and optional alternatives.

### Error envelope

```json
{
  "error": {
    "code": "RESERVATION_CONFLICT",
    "message": "That time is no longer available.",
    "request_id": "uuid",
    "details": {}
  }
}
```

Use `400` malformed request, `401` unauthenticated, `403` unauthorized, `404` hidden/not found, `409` domain conflict, `422` schema/domain validation, `429` rate limited, `503` dependency unavailable and `500` unexpected error. Public messages are localized where user-facing and never expose stack traces, SQL, credentials or provider payloads.

## WebSocket API

### Endpoint

`GET /api/v1/voice-sessions/{session_id}/stream?token=...`

The single-use, short-lived token is scoped to the restaurant and session. The server validates origin, connection limits and negotiated audio format. Tokens should preferably use an authorization mechanism that avoids long-lived query-string credentials; query values must never be logged.

### Client-to-server events

| Event | Main fields | Purpose |
|---|---|---|
| `session.start` | protocol version, audio format, preferred language | Confirm negotiation |
| `audio.append` | sequence, timestamp, encoded audio payload | Stream ordered input frames |
| `audio.commit` | final sequence | Mark a completed utterance when client VAD is used |
| `text.submit` | text, language hint | Browser text fallback |
| `playback.interrupted` | last played sequence | Signal barge-in/client cancellation |
| `session.end` | reason | Graceful close |
| `ping` | timestamp | Keepalive |

### Server-to-client events

| Event | Main fields | Purpose |
|---|---|---|
| `session.ready` | session/correlation IDs, negotiated settings | Connection accepted |
| `transcript.partial` / `transcript.final` | text, language, confidence | Recognition updates |
| `assistant.text.delta` / `assistant.text.final` | text, language, turn ID | Display response |
| `assistant.audio` | sequence, turn ID, audio payload | Stream synthesized output |
| `assistant.audio.end` | turn ID | Playback boundary |
| `assistant.cancel` | turn ID, reason | Stop obsolete playback on interruption |
| `handoff.status` | requested/connecting/connected/unavailable | Handoff lifecycle |
| `error` | stable code, safe message, recoverable flag | Protocol or processing failure |
| `pong` | timestamp | Keepalive response |

Every event has `type`, `event_id`, `session_id` and timestamp. Audio frames have monotonically increasing sequence numbers. Payload size and event rate are bounded. The server uses backpressure, discards obsolete synthesized audio after cancellation, and closes with documented WebSocket codes for authentication failure, unsupported protocol, limits or internal failure.

## Future Twilio contracts

Stage 9 will add a webhook that returns TwiML and a separate Twilio Media Streams WebSocket adapter. It will validate Twilio signatures and translate `connected`, `start`, `media`, `mark` and `stop` events into the internal session protocol. Twilio-specific details will not leak into LangGraph or reservation services.
