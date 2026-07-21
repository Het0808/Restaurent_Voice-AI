"""Build and compile the deterministic LangGraph workflow."""

from typing import Any

from langgraph.graph import END, START, StateGraph

from restaurant_voice_ai.conversation.models import ConversationDependencies
from restaurant_voice_ai.conversation.nodes import (
    cancel_reservation,
    check_availability,
    classify_intent,
    compose_response,
    create_reservation,
    extract_entities,
    modify_reservation,
    retrieve_knowledge,
)
from restaurant_voice_ai.conversation.nodes.handle_error import handle_error
from restaurant_voice_ai.conversation.nodes.handle_greeting import handle_greeting
from restaurant_voice_ai.conversation.nodes.handle_unsupported import handle_unsupported
from restaurant_voice_ai.conversation.nodes.initialize import initialize
from restaurant_voice_ai.conversation.nodes.request_clarification import request_clarification
from restaurant_voice_ai.conversation.nodes.validate_request import validate_request
from restaurant_voice_ai.conversation.routers import (
    CANCEL_RESERVATION,
    CHECK_AVAILABILITY,
    CLASSIFY_INTENT,
    COMPOSE_RESPONSE,
    CREATE_RESERVATION,
    EXTRACT_ENTITIES,
    HANDLE_ERROR,
    HANDLE_GREETING,
    HANDLE_UNSUPPORTED,
    INITIALIZE,
    MODIFY_RESERVATION,
    REQUEST_CLARIFICATION,
    RETRIEVE_KNOWLEDGE,
    VALIDATE_REQUEST,
    route_after_operation,
    route_after_validation,
)
from restaurant_voice_ai.conversation.state import ConversationState


def build_conversation_graph(dependencies: ConversationDependencies) -> Any:
    graph = StateGraph(ConversationState)
    nodes = {
        INITIALIZE: initialize,
        CLASSIFY_INTENT: classify_intent.build_node(dependencies),
        EXTRACT_ENTITIES: extract_entities.build_node(dependencies),
        VALIDATE_REQUEST: validate_request,
        RETRIEVE_KNOWLEDGE: retrieve_knowledge.build_node(dependencies),
        CHECK_AVAILABILITY: check_availability.build_node(dependencies),
        CREATE_RESERVATION: create_reservation.build_node(dependencies),
        CANCEL_RESERVATION: cancel_reservation.build_node(dependencies),
        MODIFY_RESERVATION: modify_reservation.build_node(dependencies),
        REQUEST_CLARIFICATION: request_clarification,
        COMPOSE_RESPONSE: compose_response.compose_response,
        HANDLE_GREETING: handle_greeting,
        HANDLE_UNSUPPORTED: handle_unsupported,
        HANDLE_ERROR: handle_error,
    }
    for name, node in nodes.items():
        graph.add_node(name, node)
    graph.add_edge(START, INITIALIZE)
    graph.add_edge(INITIALIZE, CLASSIFY_INTENT)
    graph.add_edge(CLASSIFY_INTENT, EXTRACT_ENTITIES)
    graph.add_edge(EXTRACT_ENTITIES, VALIDATE_REQUEST)
    graph.add_conditional_edges(VALIDATE_REQUEST, route_after_validation)
    for operation in (
        RETRIEVE_KNOWLEDGE,
        CHECK_AVAILABILITY,
        CREATE_RESERVATION,
        CANCEL_RESERVATION,
        MODIFY_RESERVATION,
    ):
        graph.add_conditional_edges(operation, route_after_operation)
    for terminal in (
        REQUEST_CLARIFICATION,
        COMPOSE_RESPONSE,
        HANDLE_GREETING,
        HANDLE_UNSUPPORTED,
        HANDLE_ERROR,
    ):
        graph.add_edge(terminal, END)
    return graph.compile()
