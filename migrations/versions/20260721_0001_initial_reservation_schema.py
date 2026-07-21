"""Create restaurant tables, reservations, and call sessions.

Revision ID: 20260721_0001
Revises: None
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260721_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

reservation_status = sa.Enum(
    "pending", "confirmed", "cancelled", "completed", "no_show", name="reservation_status"
)
call_session_status = sa.Enum("started", "completed", "failed", name="call_session_status")


def upgrade() -> None:
    op.create_table(
        "restaurant_tables",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("table_number", sa.Integer(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("area", sa.String(length=80), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("capacity >= 1", name="ck_restaurant_tables_capacity_positive"),
        sa.CheckConstraint("table_number > 0", name="ck_restaurant_tables_number_positive"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("table_number"),
    )
    op.create_table(
        "call_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("external_call_id", sa.String(length=128), nullable=True),
        sa.Column("customer_phone", sa.String(length=32), nullable=True),
        sa.Column("detected_language", sa.String(length=8), nullable=True),
        sa.Column("status", call_session_status, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_call_id"),
    )
    op.create_table(
        "reservations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("confirmation_code", sa.String(length=20), nullable=False),
        sa.Column("customer_name", sa.String(length=160), nullable=False),
        sa.Column("customer_phone", sa.String(length=32), nullable=False),
        sa.Column("customer_email", sa.String(length=254), nullable=True),
        sa.Column("party_size", sa.Integer(), nullable=False),
        sa.Column("reservation_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reservation_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", reservation_status, nullable=False),
        sa.Column("special_requests", sa.Text(), nullable=True),
        sa.Column("language", sa.String(length=8), nullable=True),
        sa.Column("restaurant_table_id", sa.Uuid(), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("party_size > 0", name="ck_reservations_party_size_positive"),
        sa.CheckConstraint(
            "reservation_end > reservation_start", name="ck_reservations_valid_time_range"
        ),
        sa.ForeignKeyConstraint(
            ["restaurant_table_id"], ["restaurant_tables.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_reservations_confirmation_code", "reservations", ["confirmation_code"], unique=True
    )
    op.create_index("ix_reservations_customer_phone", "reservations", ["customer_phone"])
    op.create_index("ix_reservations_reservation_start", "reservations", ["reservation_start"])
    op.create_index("ix_reservations_status", "reservations", ["status"])
    op.create_index(
        "ix_reservations_table_times",
        "reservations",
        ["restaurant_table_id", "reservation_start", "reservation_end"],
    )


def downgrade() -> None:
    op.drop_table("reservations")
    op.drop_table("call_sessions")
    op.drop_table("restaurant_tables")
    reservation_status.drop(op.get_bind(), checkfirst=True)
    call_session_status.drop(op.get_bind(), checkfirst=True)
