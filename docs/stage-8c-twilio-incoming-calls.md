# Stage 8C — Twilio Incoming Calls

Stage 8C uses Twilio speech `<Gather>` webhooks rather than introducing a second streaming-audio implementation. Telephony authentication and TwiML live in `telephony/`; the existing conversation service remains the only LangGraph orchestration authority, and existing typed tools remain the only database mutation path.

## Call flow

1. Twilio signs and posts call metadata to `/api/v1/voice/incoming`.
2. The API validates the signature, idempotently creates the call session, and returns welcome-and-gather TwiML.
3. Twilio posts `SpeechResult` and confidence to `/api/v1/voice/process-speech`.
4. Empty or low-confidence results use a bounded retry policy. The third failure transfers to staff or ends gracefully.
5. Valid text uses the stable `twilio-{CallSid}` conversation ID and existing Redis memory, LangGraph, Gemini fallback, confirmation state, tools, and PostgreSQL audit.
6. Twilio lifecycle callbacks update the call record idempotently.

## Safety boundaries

- Every webhook is signature checked against the configured external URL.
- Form and transcript lengths are bounded.
- Phone numbers are never used as metric labels and existing log redaction masks them.
- Gemini receives only the bounded utterance and recent safe conversation state.
- The tool dispatcher is allowlisted and validates typed arguments.
- Create, modify, and cancel tools require explicit confirmation and idempotency.
- Webhook failures return generic caller-safe TwiML.

## Limitations

- Twilio `<Gather>` is turn-based; true media-stream barge-in is not part of Stage 8C.
- Voice selection is configured globally; automatic per-turn Twilio language switching is not yet implemented.
- Staff transfer uses direct `<Dial>` and does not presently implement an agent availability queue.
- Real Twilio and Gemini requests require customer credentials and were not used by offline tests.
