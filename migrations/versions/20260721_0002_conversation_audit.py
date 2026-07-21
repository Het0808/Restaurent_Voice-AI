"""Add safe conversation audit history.

Revision ID: 20260721_0002
Revises: 20260721_0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260721_0002"
down_revision: str | None = "20260721_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversation_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.String(64), nullable=False),
        sa.Column("channel", sa.String(16), nullable=False),
        sa.Column("language", sa.String(16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("total_turns", sa.Integer(), nullable=False),
        sa.Column("safe_metadata", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("conversation_id"),
    )
    op.create_index(
        "ix_conversation_sessions_conversation_id", "conversation_sessions", ["conversation_id"]
    )
    op.create_table(
        "conversation_turns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.String(64), nullable=False),
        sa.Column("turn_number", sa.Integer(), nullable=False),
        sa.Column("user_message_masked", sa.Text(), nullable=False),
        sa.Column("assistant_message", sa.Text(), nullable=False),
        sa.Column("intent", sa.String(48), nullable=False),
        sa.Column("response_type", sa.String(48), nullable=False),
        sa.Column("tool_name", sa.String(64)),
        sa.Column("tool_success", sa.Boolean()),
        sa.Column("confirmation_status", sa.String(48)),
        sa.Column("model_provider", sa.String(48)),
        sa.Column("fallback_used", sa.Boolean(), nullable=False),
        sa.Column("latency_ms", sa.Float()),
        sa.Column("citations", sa.JSON(), nullable=False),
        sa.Column("error_code", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("conversation_id", "turn_number", name="uq_conversation_turn_number"),
    )
    op.create_index(
        "ix_conversation_turns_conversation_id", "conversation_turns", ["conversation_id"]
    )
    op.create_table(
        "tool_audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.String(64), nullable=False),
        sa.Column("turn_number", sa.Integer(), nullable=False),
        sa.Column("tool_name", sa.String(64), nullable=False),
        sa.Column("operation_type", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("idempotency_key_hash", sa.String(64)),
        sa.Column("reservation_id", sa.String(64)),
        sa.Column("safe_arguments", sa.JSON(), nullable=False),
        sa.Column("error_code", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tool_audit_conversation_id", "tool_audit_events", ["conversation_id"])


def downgrade() -> None:
    op.drop_table("tool_audit_events")
    op.drop_table("conversation_turns")
    op.drop_table("conversation_sessions")
