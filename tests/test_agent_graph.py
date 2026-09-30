"""Tests for Phase 9 LangGraph routing."""

import pytest

from backend.app.agent.graph import Intent, agent_graph


@pytest.mark.parametrize(
    ("message", "intent", "next_step"),
    [
        ("Can I get a refund?", Intent.POLICY, "rag"),
        ("Where is my order?", Intent.ORDER, "order_tool"),
        ("Why was my payment charged twice?", Intent.PAYMENT, "payment_tool"),
        ("Please connect me to a human agent.", Intent.HUMAN, "human_escalation"),
        ("My order is missing and this is a complaint.", Intent.COMPLEX, "multiple_tools"),
        ("What can you help me with?", Intent.GENERAL, "general_response"),
    ],
)
def test_agent_graph_routes_requests(
    message: str,
    intent: Intent,
    next_step: str,
) -> None:
    result = agent_graph.invoke({"user_message": message})

    assert result["intent"] == intent
    assert result["next_step"] == next_step
    assert result["trace"] == ["classify_request", intent.value]
