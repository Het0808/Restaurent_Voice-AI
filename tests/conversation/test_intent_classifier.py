import pytest

from restaurant_voice_ai.conversation.enums import Intent
from restaurant_voice_ai.conversation.nodes.classify_intent import RuleBasedIntentClassifier


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("message", "intent"),
    [
        ("hello", Intent.GREETING),
        ("cancel reservation RSV-123456", Intent.CANCEL_RESERVATION),
        ("change reservation RSV-123456", Intent.MODIFY_RESERVATION),
        ("Book a table for four", Intent.CREATE_RESERVATION),
        ("Is a table available tomorrow at 7 PM for four people?", Intent.CHECK_AVAILABILITY),
        ("Does paneer tikka contain dairy?", Intent.KNOWLEDGE_QUERY),
        ("Does this dish contain nuts?", Intent.KNOWLEDGE_QUERY),
        ("Is paneer tikka vegetarian?", Intent.KNOWLEDGE_QUERY),
        ("What ingredients are in biryani?", Intent.KNOWLEDGE_QUERY),
        ("Do you have gluten-free options?", Intent.KNOWLEDGE_QUERY),
        ("What is on the menu?", Intent.KNOWLEDGE_QUERY),
        ("What time do you open?", Intent.KNOWLEDGE_QUERY),
        ("Where are you located?", Intent.KNOWLEDGE_QUERY),
        ("What is your cancellation policy?", Intent.KNOWLEDGE_QUERY),
        ("What food is available?", Intent.KNOWLEDGE_QUERY),
        ("weather today", Intent.UNSUPPORTED),
    ],
)
async def test_rule_classifier(message: str, intent: Intent) -> None:
    result = await RuleBasedIntentClassifier().classify(message, "en")
    assert result.intent is intent
