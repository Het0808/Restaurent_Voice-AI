from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from restaurant_voice_ai.conversation.enums import Intent
from restaurant_voice_ai.conversation.nodes.extract_entities import RuleBasedEntityExtractor


@pytest.mark.asyncio
async def test_extracts_create_entities_and_tomorrow_deterministically() -> None:
    def now() -> datetime:
        return datetime(2030, 1, 2, 10, tzinfo=ZoneInfo("Asia/Kolkata"))

    extractor = RuleBasedEntityExtractor("Asia/Kolkata", now=now)
    result = await extractor.extract(
        "Book tomorrow at 7 PM for four, my name is Asha and phone is +91 98765 43210",
        Intent.CREATE_RESERVATION,
        "en",
    )
    assert result.reservation_date == "2030-01-03"
    assert result.reservation_time == "19:00"
    assert result.party_size == 4
    assert result.customer_name == "Asha"
    assert result.customer_phone == "+919876543210"


@pytest.mark.asyncio
async def test_modify_fields_are_requested_fields() -> None:
    result = await RuleBasedEntityExtractor("Asia/Kolkata").extract(
        "Change reservation RSV-123456 to 2030-03-04 at 19:00 for 5",
        Intent.MODIFY_RESERVATION,
        "en",
    )
    assert result.reservation_id == "RSV-123456"
    assert result.requested_date == "2030-03-04"
    assert result.requested_time == "19:00"
    assert result.requested_party_size == 5
