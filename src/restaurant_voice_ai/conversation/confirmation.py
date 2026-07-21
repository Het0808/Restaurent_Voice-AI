"""Deterministic mutation confirmation and rejection detection."""

import re
from enum import StrEnum


class ConfirmationDecision(StrEnum):
    AFFIRMATIVE = "affirmative"
    NEGATIVE = "negative"
    CORRECTION = "correction"
    UNKNOWN = "unknown"


AFFIRMATIVE = (
    "yes",
    "confirm",
    "proceed",
    "do it",
    "correct",
    "that's right",
    "that’s right",
    "yes please",
)
NEGATIVE = ("no", "cancel", "stop", "never mind", "do not proceed", "don't proceed")
CORRECTION = ("actually", "change", "make it", "use another", "not ")


def detect_confirmation(message: str) -> ConfirmationDecision:
    normalized = re.sub(r"[^\w'’ ]", " ", message.casefold())
    normalized = " ".join(normalized.split())
    if any(term in normalized for term in CORRECTION):
        return ConfirmationDecision.CORRECTION
    if normalized in NEGATIVE or any(normalized.startswith(f"{term} ") for term in NEGATIVE):
        return ConfirmationDecision.NEGATIVE
    if normalized in AFFIRMATIVE or any(normalized.startswith(f"{term} ") for term in AFFIRMATIVE):
        return ConfirmationDecision.AFFIRMATIVE
    return ConfirmationDecision.UNKNOWN
