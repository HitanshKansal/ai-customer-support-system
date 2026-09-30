"""Tests for Phase 11 agent and capability integration."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from backend.app.agent.runtime import AgentDependencies, AgentRequest, SupportAgent
from backend.app.agent.memory import ConversationMemory
from backend.app.agent.tools import (
    OrderStatusResult,
    PaymentStatusResult,
    TicketResult,
)
from backend.app.db.models import PaymentStatus, TicketPriority, TicketStatus
from backend.app.knowledge.rag import RagResponse


class FakeRag:
    async def answer(self, session, question: str) -> RagResponse:
        return RagResponse(answer="Use the refund policy.", sources=["refund_policy.md"])


async def fake_order(session, request):
    return OrderStatusResult(
        order_number=request.order_number,
        status="shipped",
        total_amount="25.00",
        currency="USD",
        created_at=datetime.now(timezone.utc),
    )


async def fake_payment(session, request):
    return PaymentStatusResult(
        order_number=request.order_number,
        status=PaymentStatus.COMPLETED,
        amount="25.00",
        transaction_id="txn-1",
        created_at=datetime.now(timezone.utc),
    )


async def fake_ticket(session, request):
    return TicketResult(
        ticket_id=uuid4(), status=TicketStatus.OPEN, priority=request.priority
    )


async def fake_escalation(session, request):
    return TicketResult(
        ticket_id=uuid4(), status=TicketStatus.IN_PROGRESS, priority=TicketPriority.URGENT
    )


@pytest.fixture
def agent() -> SupportAgent:
    return SupportAgent(
        AgentDependencies(
            rag=FakeRag(),
            check_order=fake_order,
            check_payment=fake_payment,
            create_ticket=fake_ticket,
            escalate=fake_escalation,
        )
    )


@pytest.mark.asyncio
async def test_policy_request_uses_rag(agent: SupportAgent) -> None:
    result = await agent.handle(
        None,
        AgentRequest(user_message="Can I get a refund?", customer_id=uuid4()),
    )

    assert result.route == "rag"
    assert result.sources == ["refund_policy.md"]


@pytest.mark.asyncio
async def test_order_request_uses_order_tool(agent: SupportAgent) -> None:
    result = await agent.handle(
        None,
        AgentRequest(user_message="Where is order ORD-123?", customer_id=uuid4()),
    )

    assert result.route == "order_tool"
    assert result.tool_result["status"] == "shipped"


@pytest.mark.asyncio
async def test_complex_request_runs_order_and_ticket_tools(agent: SupportAgent) -> None:
    result = await agent.handle(
        None,
        AgentRequest(
            user_message="My order ORD-123 is missing and this is a complaint.",
            customer_id=uuid4(),
        ),
    )

    assert result.route == "multiple_tools"
    assert isinstance(result.tool_result, list)
    assert len(result.tool_result) == 2


@pytest.mark.asyncio
async def test_follow_up_can_use_remembered_order(agent: SupportAgent) -> None:
    class MemoryWithOrder(ConversationMemory):
        async def load_recent(self, session, conversation_id):
            from backend.app.agent.memory import MemoryTurn
            from backend.app.db.models import MessageRole

            return [MemoryTurn(MessageRole.USER, "My order ORD-45821 is late.")]

        async def record_exchange(self, **kwargs):
            return None

    agent.dependencies = AgentDependencies(
        rag=FakeRag(),
        check_order=fake_order,
        check_payment=fake_payment,
        create_ticket=fake_ticket,
        escalate=fake_escalation,
        memory=MemoryWithOrder(),
    )

    result = await agent.handle(
        None,
        AgentRequest(user_message="When will it arrive?", customer_id=uuid4()),
    )

    assert result.route == "order_tool"
    assert result.tool_result["order_number"] == "ORD-45821"
