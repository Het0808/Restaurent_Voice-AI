"""ORM model registry used by Alembic."""

from restaurant_voice_ai.db.models.call_session import CallSession, CallSessionStatus
from restaurant_voice_ai.db.models.reservation import Reservation, ReservationStatus
from restaurant_voice_ai.db.models.restaurant_table import RestaurantTable

__all__ = [
    "CallSession",
    "CallSessionStatus",
    "Reservation",
    "ReservationStatus",
    "RestaurantTable",
]
