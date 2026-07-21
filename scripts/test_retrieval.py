"""Read-only diagnostic for the configured Stage 4 retrieval service."""

import asyncio

from restaurant_voice_ai.core.config import get_settings
from restaurant_voice_ai.rag.dependencies import build_rag_service

QUERY = "Does paneer tikka contain dairy?"


async def diagnose() -> None:
    settings = get_settings()
    service = build_rag_service(settings)
    results = await service.search(QUERY)
    print(f"Provider: {settings.embedding_provider}")
    print(f"Model: {settings.embedding_model_name}")
    print(f"Chroma path: {settings.chroma_persist_directory}")
    print(f"Collection: {settings.chroma_collection_name}")
    print(f"Result count: {len(results)}")
    for result in results:
        preview = " ".join(result.chunk.text.split())[:160]
        print(
            f"- source={result.chunk.source} score={result.hybrid_score:.4f} "
            f"section={result.chunk.section!r} preview={preview!r}"
        )


def main() -> int:
    asyncio.run(diagnose())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
