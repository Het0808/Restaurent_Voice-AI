"""Extend call sessions for Twilio lifecycle tracking.

Revision ID: 20260722_0003
Revises: 20260721_0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260722_0003"
down_revision: str | None = "20260721_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE call_sessions ALTER COLUMN status TYPE varchar(24) USING status::text")
    op.execute("DROP TYPE IF EXISTS call_session_status")
    op.add_column("call_sessions", sa.Column("destination_phone", sa.String(32)))
    op.add_column("call_sessions", sa.Column("direction", sa.String(32)))
    op.add_column("call_sessions", sa.Column("duration_seconds", sa.Integer()))
    op.add_column(
        "call_sessions",
        sa.Column("escalated", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("call_sessions", sa.Column("escalation_reason", sa.String(160)))
    op.add_column("call_sessions", sa.Column("reservation_outcome", sa.String(64)))
    op.add_column("call_sessions", sa.Column("error_details", sa.Text()))


def downgrade() -> None:
    op.drop_column("call_sessions", "error_details")
    op.drop_column("call_sessions", "reservation_outcome")
    op.drop_column("call_sessions", "escalation_reason")
    op.drop_column("call_sessions", "escalated")
    op.drop_column("call_sessions", "duration_seconds")
    op.drop_column("call_sessions", "direction")
    op.drop_column("call_sessions", "destination_phone")
    status_enum = sa.Enum("started", "completed", "failed", name="call_session_status")
    status_enum.create(op.get_bind(), checkfirst=True)
    op.execute(
        "UPDATE call_sessions SET status = CASE "
        "WHEN status = 'completed' THEN 'completed' "
        "WHEN status = 'failed' THEN 'failed' ELSE 'started' END"
    )
    op.execute(
        "ALTER TABLE call_sessions ALTER COLUMN status TYPE call_session_status "
        "USING status::call_session_status"
    )
