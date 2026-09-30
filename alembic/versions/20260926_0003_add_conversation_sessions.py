"""add session identifiers for conversation memory

Revision ID: 20260926_0003
Revises: 20260926_0002
Create Date: 2026-09-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260926_0003"
down_revision: str | None = "20260926_0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "conversation_messages",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.alter_column(
        "conversation_messages",
        "ticket_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.create_index(
        op.f("ix_conversation_messages_session_id"),
        "conversation_messages",
        ["session_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_conversation_messages_session_id"),
        table_name="conversation_messages",
    )
    op.alter_column(
        "conversation_messages",
        "ticket_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.drop_column("conversation_messages", "session_id")
