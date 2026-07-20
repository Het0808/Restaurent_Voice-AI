# Project Context

## Project

**Multilingual AI Restaurant Voice Receptionist**

## Objective

Build a portfolio-grade, production-minded AI voice receptionist that can receive restaurant phone calls and communicate naturally in English, Hindi, and Gujarati. The system should answer questions from approved restaurant documents, help callers complete reservation workflows against live transactional data, handle conversational interruptions, and transfer callers to a human when appropriate.

The application will separate telephony, audio processing, speech-to-text, text-to-speech, retrieval-augmented generation, LangGraph orchestration, database access, and business logic. It will prioritize low-latency and concise spoken interactions, safe tool use, reliable reservation writes, observability, testability, and incremental development.

The language model will use explicit tools and controlled business operations. It must never execute arbitrary SQL or confirm a reservation before the corresponding database operation succeeds. Restaurant documents will be served through RAG, while live availability and reservation state will always come from PostgreSQL through validated application services.

## Planned capabilities

- Receive restaurant calls through Twilio Voice.
- Stream call audio bidirectionally with Twilio Media Streams and WebSockets.
- Recognize English, Hindi, and Gujarati speech.
- Generate concise, natural spoken responses in the caller's language.
- Answer restaurant questions using hybrid retrieval over approved documents.
- Check live availability and create reservations through controlled tools.
- Orchestrate conversation state and tool workflows with LangGraph.
- Support caller interruption, recovery, and human handoff.
- Provide structured logs, evaluation, monitoring, tests, and reproducible deployment.

## Planned technology stack

- Python 3.12
- FastAPI
- WebSockets
- Twilio Voice and bidirectional Media Streams
- LangGraph
- OpenAI tool calling
- Whisper or OpenAI speech-to-text
- OpenAI or ElevenLabs text-to-speech
- ChromaDB
- BM25 hybrid retrieval
- PostgreSQL
- SQLAlchemy 2
- Alembic
- Pydantic v2
- Redis where useful
- Docker and Docker Compose
- Pytest
- Ruff
- MyPy
- Structured logging
