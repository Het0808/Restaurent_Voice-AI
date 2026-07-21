"""Stable conversation routing and response enums."""

from enum import StrEnum


class Intent(StrEnum):
    GREETING = "greeting"
    KNOWLEDGE_QUERY = "knowledge_query"
    CHECK_AVAILABILITY = "check_availability"
    CREATE_RESERVATION = "create_reservation"
    CANCEL_RESERVATION = "cancel_reservation"
    MODIFY_RESERVATION = "modify_reservation"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"


class ResponseType(StrEnum):
    ANSWER = "answer"
    CONFIRMATION = "confirmation"
    CLARIFICATION = "clarification"
    ERROR = "error"
    UNSUPPORTED = "unsupported"


class NextAction(StrEnum):
    NONE = "none"
    ASK_CUSTOMER_NAME = "ask_customer_name"
    ASK_CUSTOMER_PHONE = "ask_customer_phone"
    ASK_RESERVATION_DATE = "ask_reservation_date"
    ASK_RESERVATION_TIME = "ask_reservation_time"
    ASK_PARTY_SIZE = "ask_party_size"
    ASK_RESERVATION_ID = "ask_reservation_id"
    ASK_REQUESTED_CHANGE = "ask_requested_change"
    CONFIRM_RESERVATION = "confirm_reservation"
    RETRY = "retry"
    HANDOFF_RECOMMENDED = "handoff_recommended"
    AWAIT_CONFIRMATION = "await_confirmation"


class ConfirmationStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    EXPIRED = "expired"
    EXECUTING = "executing"
    COMPLETED = "completed"


class ConversationStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    RESET = "reset"
