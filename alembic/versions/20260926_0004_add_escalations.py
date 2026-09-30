"""add human escalation workflow records

Revision ID: 20260926_0004
Revises: 20260926_0003
Create Date: 2026-09-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260926_0004"
down_revision: str | None = "20260926_0003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


escalation_status = postgresql.ENUM(
    "open",
    "acknowledged",
    "in_progress",
    "resolved",
    "cancelled",
    name="escalation_status",
)


def upgrade() -> None:
    op.create_table(
        "escalations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_agent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", escalation_status, nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["assigned_agent_id"],
            ["users.id"],
            name=op.f("fk_escalations_assigned_agent_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["users.id"],
            name=op.f("fk_escalations_customer_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["tickets.id"],
            name=op.f("fk_escalations_ticket_id_tickets"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_escalations")),
        sa.UniqueConstraint("ticket_id", name=op.f("uq_escalations_ticket_id")),
    )
    op.create_index(op.f("ix_escalations_ticket_id"), "escalations", ["ticket_id"])
    op.create_index(op.f("ix_escalations_customer_id"), "escalations", ["customer_id"])
    op.create_index(
        op.f("ix_escalations_assigned_agent_id"), "escalations", ["assigned_agent_id"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_escalations_assigned_agent_id"), table_name="escalations")
    op.drop_index(op.f("ix_escalations_customer_id"), table_name="escalations")
    op.drop_index(op.f("ix_escalations_ticket_id"), table_name="escalations")
    op.drop_table("escalations")
    escalation_status.drop(op.get_bind(), checkfirst=True)
