"""Ingest the default restaurant knowledge directory into Chroma."""

import asyncio
import sys
import traceback
from pathlib import Path

from restaurant_voice_ai.core.config import get_settings
from restaurant_voice_ai.rag.dependencies import build_rag_service


async def ingest() -> None:
    service = build_rag_service(get_settings())
    result = await service.ingest_directory(Path("data/knowledge"))
    print(f"Indexed {result.chunk_count} chunks from {result.source_count} sources.")
    for source in result.sources:
        print(f"- {source}")


def main() -> int:
    settings = get_settings()
    try:
        asyncio.run(ingest())
    except Exception as exc:
        message = str(exc).strip() or repr(exc)
        for secret in (settings.google_api_key, settings.openai_api_key):
            if secret:
                message = message.replace(secret, "[REDACTED]")
        print(f"Knowledge ingestion failed: {type(exc).__name__}: {message}", file=sys.stderr)
        if settings.app_env == "development":
            rendered = "".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__, chain=False)
            )
            for secret in (settings.google_api_key, settings.openai_api_key):
                if secret:
                    rendered = rendered.replace(secret, "[REDACTED]")
            print(rendered, file=sys.stderr, end="")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
