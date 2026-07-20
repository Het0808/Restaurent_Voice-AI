# LangGraph Conversation Design

## Role and boundaries

LangGraph coordinates a conversation turn; it does not own transport, persistence, audio conversion or SQL. Nodes consume typed state and return explicit state updates. External effects occur only in allowlisted tool nodes. The workflow uses current, non-deprecated LangGraph patterns when implemented.

## Conversation state

| Field | Purpose |
|---|---|
| `session_id`, `correlation_id` | Trace the call and current turn |
| `restaurant_id` | Scope every retrieval and business operation |
| `messages` | Bounded conversational messages needed for the current context |
| `transcript` | Latest finalized caller utterance |
| `language` | `en`, `hi` or `gu`, plus confidence/source metadata |
| `intent` | FAQ, create, find, modify, cancel, handoff, unsupported or unclear |
| `reservation_draft` | Validated slots: name, phone, date/time, party size, duration and requests |
| `reservation_id` | Authoritative target returned/found by a tool |
| `missing_fields` | Required fields still to collect |
| `confirmation_status` | None, awaiting caller, accepted or rejected |
| `retrieval_query` | Scoped FAQ query |
| `retrieved_context` | Ranked chunks with document/source metadata |
| `tool_request` | Allowlisted tool name and validated arguments |
| `tool_result` | Structured success, conflict or failure result |
| `response_text` | Concise final text in the selected language |
| `handoff_reason` | Explicit request or classified escalation reason |
| `retry_count`, `error` | Bounded recovery state; sanitized error category |

Do not place secrets, provider clients, database sessions or arbitrary SQL in state. Persist/checkpoint only the minimum fields needed for recovery and apply retention controls.

## Nodes

1. `normalize_input`: sanitize the final transcript, establish restaurant scope and reject empty/oversized input.
2. `resolve_language`: honor explicit preference, otherwise use detection with a safe default.
3. `classify_intent`: choose one supported intent without performing side effects.
4. `prepare_faq_query`: rewrite only enough to retrieve restaurant information.
5. `retrieve_faq`: execute restaurant-scoped hybrid retrieval.
6. `extract_reservation_fields`: extract typed candidate fields from caller language.
7. `validate_reservation_fields`: normalize dates in restaurant timezone, validate party size and compute missing fields.
8. `ask_for_missing_fields`: produce one short question for the most important missing value.
9. `request_confirmation`: summarize a proposed write and ask for explicit caller approval.
10. `select_tool`: map the confirmed intent to one allowlisted tool.
11. `execute_tool`: invoke the typed application service and store its authoritative result.
12. `compose_response`: ground FAQ answers in retrieved content and writes in tool results.
13. `prepare_handoff`: record a safe reason and return transport-neutral handoff instructions.
14. `recover_error`: classify recoverable failures, retry within limits or offer handoff.
15. `finish_turn`: return final text and metadata to the session coordinator.

## Conditional edges

```text
START -> normalize_input -> resolve_language -> classify_intent

classify_intent:
  FAQ        -> prepare_faq_query -> retrieve_faq -> compose_response
  CREATE     -> extract_reservation_fields -> validate_reservation_fields
  FIND       -> extract_reservation_fields -> validate_reservation_fields
  MODIFY     -> extract_reservation_fields -> validate_reservation_fields
  CANCEL     -> extract_reservation_fields -> validate_reservation_fields
  HANDOFF    -> prepare_handoff
  UNCLEAR    -> compose_response (clarifying question)
  UNSUPPORTED-> compose_response (boundary + handoff offer)

validate_reservation_fields:
  missing fields             -> ask_for_missing_fields
  read-only find complete    -> select_tool -> execute_tool
  write fields complete      -> request_confirmation
  invalid/unresolvable       -> compose_response

request_confirmation:
  accepted -> select_tool -> execute_tool
  rejected -> compose_response
  unclear  -> request_confirmation (bounded; then handoff)

execute_tool:
  success  -> compose_response
  conflict -> compose_response (alternatives)
  retryable failure and retry_count below limit -> recover_error -> execute_tool
  permanent/exhausted failure -> recover_error -> prepare_handoff or compose_response

compose_response -> finish_turn -> END
prepare_handoff -> finish_turn -> END
```

Each run must have recursion/step limits. Loops are bounded and cancellation from caller interruption propagates to active model/provider work.

## Tool definitions

All tool inputs are schema-validated, restaurant-scoped and generated from state—not free-form SQL.

| Tool | Required input | Result |
|---|---|---|
| `search_restaurant_faq` | `restaurant_id`, query, language, limit | Ranked approved passages and sources |
| `check_table_availability` | Restaurant, timezone-aware start, party size, duration | Available slots/table options; no hold implied |
| `find_reservations` | Restaurant plus caller phone and bounded date/reference filters | Minimal matching reservation summaries |
| `create_reservation` | Idempotency key, customer details, start, duration, party size, optional requests/language | Committed reservation or conflict/alternatives |
| `modify_reservation` | Reservation ID, expected version, explicitly changed fields, idempotency key | Committed updated reservation or conflict |
| `cancel_reservation` | Reservation ID, expected version, idempotency key | Committed cancellation/current cancelled state or failure |
| `request_human_handoff` | Session ID and allowlisted reason | Accepted/unavailable handoff status |

Write tools require explicit caller confirmation in graph state. Authorization and ownership are independently checked by the service. Tool outputs use stable statuses such as `success`, `conflict`, `not_found`, `validation_error`, `unauthorized`, `temporarily_unavailable`; exceptions are not exposed to the model.

## Response rules

- Match the selected language, using natural localized phrasing rather than verbose translations.
- Ask one question at a time and keep voice responses short.
- Never state unsupported FAQ facts.
- Never say a reservation is confirmed, changed or cancelled unless a successful committed tool result says so.
- For ambiguity, sensitive requests, repeated failure or explicit caller request, offer handoff.
