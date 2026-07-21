"""Stage 6 bounded LangGraph turn pipeline."""

from collections.abc import Awaitable, Callable
from typing import Any

from langchain_core.runnables import RunnableLambda
from langgraph.graph import END, START, StateGraph

from restaurant_voice_ai.conversation.state import ConversationState

INITIALIZE = "initialize"
LOAD_MEMORY = "load_conversation_memory"
MERGE_CONTEXT = "merge_context"
DETECT_CONFIRMATION = "detect_confirmation_or_correction"
INTERPRET_MESSAGE = "interpret_message"
PLAN_ACTION = "plan_action"
PERSIST_CONTEXT = "persist_context"

TurnHandler = Callable[[ConversationState], Awaitable[dict[str, Any]]]


async def _pass_state(_: ConversationState) -> dict[str, Any]:
    return {}


def create_conversation_graph(turn_handler: TurnHandler | None = None) -> Any:
    """Compile a bounded graph; dependencies remain in closures, never graph state."""
    graph = StateGraph(ConversationState)
    pass_node = RunnableLambda(_pass_state)
    graph.add_node(INITIALIZE, pass_node)
    graph.add_node(LOAD_MEMORY, pass_node)
    graph.add_node(MERGE_CONTEXT, pass_node)
    graph.add_node(DETECT_CONFIRMATION, pass_node)
    graph.add_node(INTERPRET_MESSAGE, pass_node)
    graph.add_node(PLAN_ACTION, RunnableLambda(turn_handler or _pass_state))
    graph.add_node(PERSIST_CONTEXT, pass_node)
    graph.add_edge(START, INITIALIZE)
    graph.add_edge(INITIALIZE, LOAD_MEMORY)
    graph.add_edge(LOAD_MEMORY, MERGE_CONTEXT)
    graph.add_edge(MERGE_CONTEXT, DETECT_CONFIRMATION)
    graph.add_edge(DETECT_CONFIRMATION, INTERPRET_MESSAGE)
    graph.add_edge(INTERPRET_MESSAGE, PLAN_ACTION)
    graph.add_edge(PLAN_ACTION, PERSIST_CONTEXT)
    graph.add_edge(PERSIST_CONTEXT, END)
    return graph.compile()


def build_conversation_graph(dependencies: Any) -> Any:
    """Backward-compatible Stage 5 graph constructor."""
    from restaurant_voice_ai.conversation.service import ConversationService

    return ConversationService(dependencies).graph
