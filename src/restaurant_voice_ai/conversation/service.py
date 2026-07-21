"""Public application service for one stateless conversation turn."""

from typing import Any

from restaurant_voice_ai.conversation.enums import Intent, NextAction, ResponseType
from restaurant_voice_ai.conversation.graph import build_conversation_graph
from restaurant_voice_ai.conversation.models import ConversationDependencies
from restaurant_voice_ai.schemas.conversation import ConversationMessageResponse


class ConversationService:
    def __init__(self, dependencies: ConversationDependencies) -> None:
        self.graph = build_conversation_graph(dependencies)

    async def process_message(
        self, message: str, language: str = "en", *, debug: bool = False
    ) -> ConversationMessageResponse:
        inputs = {"message": message, "language": language, "debug": debug}
        if debug:
            result: dict[str, Any] = dict(inputs)
            trace: list[dict[str, Any]] = []
            async for update in self.graph.astream(inputs, stream_mode="updates"):
                for node_name, values in update.items():
                    result.update(values)
                    trace.append({"node": node_name, "status": "completed"})
            result["trace"] = trace
        else:
            result = await self.graph.ainvoke(inputs)
        return ConversationMessageResponse(
            intent=Intent(result["intent"]),
            response_type=ResponseType(result["response_type"]),
            response_text=result["response_text"],
            next_action=NextAction(result["next_action"]),
            entities=result.get("entities", {}),
            citations=result.get("citations", []),
            availability=result.get("availability"),
            reservation=result.get("reservation"),
            trace=result.get("trace") if debug else None,
        )
