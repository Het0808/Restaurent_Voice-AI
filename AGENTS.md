# Development Rules

1. Work only inside the current repository.
2. Inspect existing files before making changes.
3. Build the project incrementally.
4. Implement only the stage explicitly requested.
5. Do not implement future stages early.
6. Keep telephony, audio, STT, TTS, RAG, LangGraph, database and business logic in separate modules.
7. Use Python 3.12 and type hints throughout.
8. Avoid deprecated FastAPI, Pydantic, LangChain and LangGraph patterns.
9. Never hardcode API keys or credentials.
10. Add configuration values to `.env.example`.
11. Add tests for implemented functionality.
12. Run relevant tests and quality checks.
13. Report failed checks honestly.
14. The LLM must never execute arbitrary SQL.
15. The LLM must never confirm a reservation before the database operation succeeds.
16. Use RAG for restaurant documents, not live reservation availability.
17. Keep spoken responses concise and natural.
18. Update `docs/progress.md` after every stage.
19. Stop after completing the requested stage.
