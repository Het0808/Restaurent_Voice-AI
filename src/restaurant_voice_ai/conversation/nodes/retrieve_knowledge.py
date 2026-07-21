"""Retrieve restaurant-document evidence only."""

import logging
from typing import Any

from restaurant_voice_ai.conversation.models import ConversationDependencies
from restaurant_voice_ai.conversation.state import ConversationState

logger = logging.getLogger(__name__)


def build_node(dependencies: ConversationDependencies) -> Any:
    async def retrieve_knowledge(state: ConversationState) -> ConversationState:
        try:
            retrieval = await dependencies.knowledge.retrieve(state["message"])
            results = retrieval.get("retrieval_results", [])
            citations = retrieval.get("citations", [])
            context = str(retrieval.get("retrieved_context", ""))
            evidence_found = bool(retrieval.get("evidence_found") and results)
            logger.debug(
                "Conversation knowledge retrieval completed",
                extra={
                    "conversation_id": state["conversation_id"],
                    "query": state["message"],
                    "result_count": len(results),
                    "result_sources": [result.get("source") for result in results],
                    "result_scores": [result.get("score") for result in results],
                },
            )
            return {
                "retrieval": retrieval,
                "retrieval_results": results,
                "retrieved_context": context,
                "citations": citations,
                "evidence_found": evidence_found,
            }
        except Exception as error:
            logger.warning(
                "Conversation knowledge retrieval failed",
                extra={
                    "conversation_id": state["conversation_id"],
                    "error_type": type(error).__name__,
                },
            )
            return {
                "retrieval": {"evidence_found": False},
                "retrieval_results": [],
                "retrieved_context": "",
                "citations": [],
                "evidence_found": False,
            }

    return retrieve_knowledge
