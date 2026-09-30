"""Tests for Phase 10 tool schemas and database query contracts."""

from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from backend.app.agent.tools import (
    CheckOrderStatusInput,
    CreateSupportTicketInput,
    EscalateToHumanInput,
    TicketPriority,
)
from backend.app.db.models import Order, Payment
from sqlalchemy import select


def test_tool_inputs_validate_and_normalize_typed_values() -> None:
    request = CreateSupportTicketInput(
        customer_id=str(uuid4()),
        subject="Package delayed",
        description="Tracking has not changed for five business days.",
    )

    assert request.priority == TicketPriority.MEDIUM
    assert request.customer_id.version == 4


def test_tool_inputs_reject_empty_order_numbers() -> None:
    with pytest.raises(ValueError):
        CheckOrderStatusInput(order_number="")


def test_escalation_accepts_optional_existing_ticket() -> None:
    ticket_id = uuid4()
    request = EscalateToHumanInput(
        customer_id=uuid4(),
        reason="Customer requested a human agent.",
        ticket_id=ticket_id,
    )

    assert request.ticket_id == ticket_id


def test_order_and_payment_queries_compile_for_postgresql() -> None:
    order_query = select(Order).where(Order.order_number == "ORD-123")
    payment_query = (
        select(Payment)
        .join(Order, Payment.order_id == Order.id)
        .where(Order.order_number == "ORD-123")
    )

    assert "orders.order_number" in str(
        order_query.compile(dialect=postgresql.dialect())
    )
    assert "JOIN orders" in str(payment_query.compile(dialect=postgresql.dialect()))
