"""Execute routed agent requests with real RAG and database tools."""

import re
from dataclasses import dataclass
from typing import Awaitable, Callable
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agent.graph import AgentState, Intent, agent_graph
from backend.app.agent.memory import ConversationMemory
from backend.app.agent.tools import (
    CheckOrderStatusInput,
    CheckPaymentStatusInput,
    CreateSupportTicketInput,
    EscalateToHumanInput,
    OrderStatusResult,
    PaymentStatusResult,
    TicketResult,
    check_order_status,
    check_payment_status,
    create_support_ticket,
    escalate_to_human,
    ToolNotFoundError,
)
from backend.app.core.errors import AppError
from backend.app.db.models import TicketPriority
from backend.app.knowledge.rag import RagResponse, RagService


class AgentRequest(BaseModel):
    """Input accepted by the integrated support agent."""

    user_message: str = Field(min_length=1, max_length=10000)
    customer_id: UUID
    conversation_id: UUID = Field(default_factory=uuid4)
    order_number: str | None = Field(default=None, max_length=50)
    ticket_id: UUID | None = None


class AgentResponse(BaseModel):
    """Consistent response envelope for API and chat adapters."""

    intent: Intent
    route: str
    answer: str
    tool_result: dict[str, object] | list[dict[str, object]] | None = None
    sources: list[str] = []
    trace: list[str] = []
    error_code: str | None = None


CheckOrderFn = Callable[[AsyncSession, CheckOrderStatusInput], Awaitable[OrderStatusResult]]
CheckPaymentFn = Callable[
    [AsyncSession, CheckPaymentStatusInput], Awaitable[PaymentStatusResult]
]
CreateTicketFn = Callable[
    [AsyncSession, CreateSupportTicketInput], Awaitable[TicketResult]
]
EscalateFn = Callable[[AsyncSession, EscalateToHumanInput], Awaitable[TicketResult]]


@dataclass(frozen=True)
class AgentDependencies:
    """Injectable production implementations for the agent runtime."""

    rag: RagService
    check_order: CheckOrderFn = check_order_status
    check_payment: CheckPaymentFn = check_payment_status
    create_ticket: CreateTicketFn = create_support_ticket
    escalate: EscalateFn = escalate_to_human
    memory: ConversationMemory | None = None


def extract_order_number(message: str) -> str | None:
    """Extract an order identifier when the user writes one in the message."""

    match = re.search(r"\b(?:order|ord)\s*[-:#]?\s*([A-Za-z0-9-]+)", message, re.I)
    return match.group(1) if match else None


def _dump_result(result: BaseModel) -> dict[str, object]:
    """Serialize a Pydantic tool result into the response envelope."""

    return result.model_dump(mode="json")


class SupportAgent:
    """Run graph routing followed by the selected real capability."""

    def __init__(self, dependencies: AgentDependencies):
        self.dependencies = dependencies

    async def handle(
        self,
        session: AsyncSession,
        request: AgentRequest,
    ) -> AgentResponse:
        """Load memory, execute the request, then persist the exchange."""

        routed_request = request
        if self.dependencies.memory is not None:
            turns = await self.dependencies.memory.load_recent(
                session, request.conversation_id
            )
            remembered_order = self.dependencies.memory.find_last_order_number(turns)
            if request.order_number is None and remembered_order is not None:
                routed_request = request.model_copy(
                    update={
                        "order_number": remembered_order,
                        "user_message": (
                            f"Order {remembered_order}: {request.user_message}"
                        ),
                    }
                )

        try:
            response = await self._handle_routed(session, routed_request)
        except AppError as exc:
            response = self._failure_response(exc)
        except Exception:
            response = AgentResponse(
                intent=Intent.GENERAL,
                route="error",
                answer="Something went wrong while handling your request. Please try again or ask for human support.",
                error_code="internal_error",
            )
        if self.dependencies.memory is not None:
            await self.dependencies.memory.record_exchange(
                session=session,
                conversation_id=request.conversation_id,
                customer_id=request.customer_id,
                user_message=request.user_message,
                assistant_message=response.answer,
                ticket_id=request.ticket_id,
            )
        return response

    async def _handle_routed(
        self,
        session: AsyncSession,
        request: AgentRequest,
    ) -> AgentResponse:
        """Route and execute one support request."""

        state: AgentState = agent_graph.invoke(
            {
                "user_message": request.user_message,
                "order_number": request.order_number,
            }
        )
        intent = state["intent"]
        order_number = request.order_number or extract_order_number(request.user_message)

        if intent is Intent.POLICY:
            rag_result: RagResponse = await self.dependencies.rag.answer(
                session, request.user_message
            )
            return AgentResponse(
                intent=intent,
                route="rag",
                answer=rag_result.answer,
                sources=rag_result.sources,
                trace=state["trace"],
            )

        if intent is Intent.ORDER:
            if order_number is None:
                return self._missing_order_response(state)
            result = await self.dependencies.check_order(
                session, CheckOrderStatusInput(order_number=order_number)
            )
            return AgentResponse(
                intent=intent,
                route="order_tool",
                answer=f"Order {result.order_number} is currently {result.status}.",
                tool_result=_dump_result(result),
                trace=state["trace"],
            )

        if intent is Intent.PAYMENT:
            if order_number is None:
                return self._missing_order_response(state)
            result = await self.dependencies.check_payment(
                session, CheckPaymentStatusInput(order_number=order_number)
            )
            return AgentResponse(
                intent=intent,
                route="payment_tool",
                answer=f"The latest payment for order {result.order_number} is {result.status.value}.",
                tool_result=_dump_result(result),
                trace=state["trace"],
            )

        if intent is Intent.HUMAN:
            result = await self.dependencies.escalate(
                session,
                EscalateToHumanInput(
                    customer_id=request.customer_id,
                    reason=request.user_message,
                    ticket_id=request.ticket_id,
                ),
            )
            return AgentResponse(
                intent=intent,
                route="human_escalation",
                answer=f"Your request has been escalated under ticket {result.ticket_id}.",
                tool_result=_dump_result(result),
                trace=state["trace"],
            )

        if intent is Intent.COMPLEX:
            return await self._handle_complex(
                session, request, state, order_number
            )

        return AgentResponse(
            intent=intent,
            route="general_response",
            answer="I can help with policies, orders, payments, or human support.",
            trace=state["trace"],
        )

    async def _handle_complex(
        self,
        session: AsyncSession,
        request: AgentRequest,
        state: AgentState,
        order_number: str | None,
    ) -> AgentResponse:
        """Check the order when possible and create a high-priority ticket."""

        results: list[dict[str, object]] = []
        if order_number is not None:
            order_result = await self.dependencies.check_order(
                session, CheckOrderStatusInput(order_number=order_number)
            )
            results.append(_dump_result(order_result))

        ticket_result = await self.dependencies.create_ticket(
            session,
            CreateSupportTicketInput(
                customer_id=request.customer_id,
                subject="Complex support complaint",
                description=request.user_message,
                priority=TicketPriority.HIGH,
            ),
        )
        results.append(_dump_result(ticket_result))
        return AgentResponse(
            intent=Intent.COMPLEX,
            route="multiple_tools",
            answer=f"I created a high-priority support ticket: {ticket_result.ticket_id}.",
            tool_result=results,
            trace=state["trace"],
        )

    @staticmethod
    def _missing_order_response(state: AgentState) -> AgentResponse:
        """Ask for the identifier required by order and payment tools."""

        return AgentResponse(
            intent=state["intent"],
            route="clarification",
            answer="Please provide your order number so I can look that up.",
            trace=state["trace"],
        )

    @staticmethod
    def _failure_response(error: AppError) -> AgentResponse:
        """Convert expected service failures into safe agent responses."""

        if isinstance(error, ToolNotFoundError):
            answer = "I could not find that record. Please verify the identifier or ask for human support."
        else:
            answer = error.message
        return AgentResponse(
            intent=Intent.GENERAL,
            route="error",
            answer=answer,
            error_code=error.code,
        )
