"""Phase 9 support-agent graph with explicit routing state."""

from enum import StrEnum
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class Intent(StrEnum):
    """Top-level request categories used by the first router."""

    POLICY = "policy"
    ORDER = "order"
    PAYMENT = "payment"
    HUMAN = "human"
    COMPLEX = "complex"
    GENERAL = "general"


class AgentState(TypedDict, total=False):
    """State passed between LangGraph nodes."""

    user_message: str
    intent: Intent
    next_step: str
    trace: list[str]
    order_number: str | None


def _append_trace(state: AgentState, node_name: str) -> list[str]:
    """Return a copied trace so nodes do not mutate caller-owned state."""

    return [*state.get("trace", []), node_name]


def classify_request(state: AgentState) -> AgentState:
    """Classify obvious request types before real LLM routing is introduced."""

    message = state["user_message"].lower()
    if any(term in message for term in ("human", "agent", "representative")):
        intent = Intent.HUMAN
    elif any(
        term in message
        for term in ("complaint", "not received", "missing", "wrong item")
    ):
        intent = Intent.COMPLEX
    elif any(term in message for term in ("payment", "charged", "charge")):
        intent = Intent.PAYMENT
    elif any(term in message for term in ("order", "shipping", "delivery")):
        intent = Intent.ORDER
    elif any(
        term in message
        for term in ("refund", "cancel", "policy", "return", "eligible")
    ):
        intent = Intent.POLICY
    else:
        intent = Intent.GENERAL

    return {
        **state,
        "intent": intent,
        "trace": _append_trace(state, "classify_request"),
    }


def route_request(state: AgentState) -> Intent:
    """Return the conditional-edge key selected by the classifier."""

    return state.get("intent", Intent.GENERAL)


def policy_node(state: AgentState) -> AgentState:
    """Declare that policy questions should use the RAG capability."""

    return {**state, "next_step": "rag", "trace": _append_trace(state, "policy")}


def order_node(state: AgentState) -> AgentState:
    """Declare that order questions should use the order-status tool."""

    return {
        **state,
        "next_step": "order_tool",
        "trace": _append_trace(state, "order"),
    }


def payment_node(state: AgentState) -> AgentState:
    """Declare that payment questions should use the payment-status tool."""

    return {
        **state,
        "next_step": "payment_tool",
        "trace": _append_trace(state, "payment"),
    }


def human_node(state: AgentState) -> AgentState:
    """Declare that explicit human requests should be escalated."""

    return {
        **state,
        "next_step": "human_escalation",
        "trace": _append_trace(state, "human"),
    }


def complex_node(state: AgentState) -> AgentState:
    """Declare that complex complaints may require multiple tools."""

    return {
        **state,
        "next_step": "multiple_tools",
        "trace": _append_trace(state, "complex"),
    }


def general_node(state: AgentState) -> AgentState:
    """Declare that general questions should receive a general response."""

    return {
        **state,
        "next_step": "general_response",
        "trace": _append_trace(state, "general"),
    }


def build_agent_graph():
    """Compile the support-agent graph with conditional routing edges."""

    graph = StateGraph(AgentState)
    graph.add_node("classify_request", classify_request)
    graph.add_node("policy", policy_node)
    graph.add_node("order", order_node)
    graph.add_node("payment", payment_node)
    graph.add_node("human", human_node)
    graph.add_node("complex", complex_node)
    graph.add_node("general", general_node)

    graph.add_edge(START, "classify_request")
    graph.add_conditional_edges(
        "classify_request",
        route_request,
        {
            Intent.POLICY: "policy",
            Intent.ORDER: "order",
            Intent.PAYMENT: "payment",
            Intent.HUMAN: "human",
            Intent.COMPLEX: "complex",
            Intent.GENERAL: "general",
        },
    )
    for node_name in ("policy", "order", "payment", "human", "complex", "general"):
        graph.add_edge(node_name, END)

    return graph.compile()


agent_graph = build_agent_graph()
