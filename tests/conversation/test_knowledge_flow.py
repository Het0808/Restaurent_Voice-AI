from pathlib import Path

import pytest

from restaurant_voice_ai.conversation.dependencies import RagKnowledgeGateway
from restaurant_voice_ai.conversation.enums import Intent
from restaurant_voice_ai.conversation.models import ConversationDependencies
from restaurant_voice_ai.conversation.nodes.classify_intent import RuleBasedIntentClassifier
from restaurant_voice_ai.conversation.nodes.extract_entities import RuleBasedEntityExtractor
from restaurant_voice_ai.conversation.service import ConversationService
from restaurant_voice_ai.core.config import Settings
from restaurant_voice_ai.rag.bm25_store import BM25Store
from restaurant_voice_ai.rag.service import RagService
from restaurant_voice_ai.rag.vector_store import ChromaVectorStore
from tests.conversation.helpers import FakeKnowledge, dependencies
from tests.rag.helpers import FakeEmbeddings


@pytest.mark.asyncio
async def test_knowledge_answer_includes_citation_and_allergy_caveat() -> None:
    knowledge = FakeKnowledge()
    response = await ConversationService(dependencies(knowledge=knowledge)).process_message(
        "Does paneer tikka contain dairy?"
    )
    assert knowledge.calls == ["Does paneer tikka contain dairy?"]
    assert response.citations
    assert response.citations[0].source == "menu.md"
    assert response.intent is Intent.KNOWLEDGE_QUERY
    assert "couldn't find" not in response.response_text


@pytest.mark.asyncio
async def test_rag_failure_is_safe_no_evidence() -> None:
    response = await ConversationService(
        dependencies(knowledge=FakeKnowledge(fail=True))
    ).process_message("What is on the menu?")
    assert response.citations == []
    assert "couldn't find" in response.response_text


@pytest.mark.asyncio
async def test_real_rag_interface_maps_menu_metadata_and_preserves_citations(
    tmp_path: Path,
) -> None:
    settings = Settings(
        app_env="test",
        cors_origins=[],
        embedding_provider="local",
        chroma_persist_directory=str(tmp_path / "chroma"),
        chroma_collection_name="conversation_knowledge",
        rag_score_threshold=0,
        rag_chunk_size=120,
        rag_chunk_overlap=20,
    )
    rag = RagService(
        settings,
        FakeEmbeddings(),
        ChromaVectorStore(settings.chroma_persist_directory, settings.chroma_collection_name),
        BM25Store(),
    )
    menu = tmp_path / "menu.md"
    menu.write_text(
        "# Menu\n\n## Paneer Tikka\n\nPaneer tikka contains dairy yogurt.",
        encoding="utf-8",
    )
    await rag.ingest_file(menu)
    base = dependencies()
    configured = ConversationDependencies(
        classifier=RuleBasedIntentClassifier(),
        extractor=RuleBasedEntityExtractor("Asia/Kolkata"),
        knowledge=RagKnowledgeGateway(rag),
        reservations=base.reservations,
    )

    response = await ConversationService(configured).process_message(
        "Does paneer tikka contain dairy?"
    )

    assert response.citations[0].source == "menu.md"
    assert response.citations[0].chunk_id
    assert response.citations[0].metadata == {"extension": ".md"}
    assert "couldn't find" not in response.response_text
    assert base.reservations.calls == []
