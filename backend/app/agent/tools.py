"""Database-backed tools exposed to the support agent."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.errors import ResourceNotFoundError
from backend.app.db.models import (
    Order,
    Payment,
    PaymentStatus,
    Escalation,
    EscalationStatus,
    Ticket,
    TicketPriority,
    TicketStatus,
    User,
)


class ToolNotFoundError(ResourceNotFoundError):
    """Raised when a tool cannot find the requested resource."""


class CheckOrderStatusInput(BaseModel):
    """Input schema for order lookup."""

    order_number: str = Field(min_length=1, max_length=50)


class CheckPaymentStatusInput(BaseModel):
    """Input schema for payment lookup by order."""

    order_number: str = Field(min_length=1, max_length=50)


class CreateSupportTicketInput(BaseModel):
    """Input schema for creating a customer support ticket."""

    customer_id: UUID
    subject: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=10000)
    priority: TicketPriority = TicketPriority.MEDIUM


class EscalateToHumanInput(BaseModel):
    """Input schema for creating or upgrading a human escalation."""

    customer_id: UUID
    reason: str = Field(min_length=1, max_length=10000)
    ticket_id: UUID | None = None


class OrderStatusResult(BaseModel):
    """Safe, structured order information for the agent."""

    order_number: str
    status: str
    total_amount: Decimal
    currency: str
    created_at: datetime


class PaymentStatusResult(BaseModel):
    """Safe, structured payment information for the agent."""

    order_number: str
    status: PaymentStatus
    amount: Decimal
    transaction_id: str | None
    created_at: datetime


class TicketResult(BaseModel):
    """Structured result for created or updated tickets."""

    ticket_id: UUID
    status: TicketStatus
    priority: TicketPriority
    escalation_id: UUID | None = None


async def check_order_status(
    session: AsyncSession,
    request: CheckOrderStatusInput,
) -> OrderStatusResult:
    """Look up one order by its customer-visible order number."""

    order = await session.scalar(
        select(Order).where(Order.order_number == request.order_number)
    )
    if order is None:
        raise ToolNotFoundError(
            f"No order was found for order number {request.order_number}"
        )

    return OrderStatusResult(
        order_number=order.order_number,
        status=order.status.value,
        total_amount=order.total_amount,
        currency=order.currency,
        created_at=order.created_at,
    )


async def check_payment_status(
    session: AsyncSession,
    request: CheckPaymentStatusInput,
) -> PaymentStatusResult:
    """Return the most recent payment attempt for an order."""

    payment = await session.scalar(
        select(Payment)
        .join(Order, Payment.order_id == Order.id)
        .where(Order.order_number == request.order_number)
        .order_by(Payment.created_at.desc())
        .limit(1)
    )
    if payment is None:
        raise ToolNotFoundError(
            f"No payment was found for order number {request.order_number}"
        )

    order = await session.get(Order, payment.order_id)
    if order is None:
        raise ToolNotFoundError("The payment references an unavailable order")

    return PaymentStatusResult(
        order_number=order.order_number,
        status=payment.status,
        amount=payment.amount,
        transaction_id=payment.transaction_id,
        created_at=payment.created_at,
    )


async def create_support_ticket(
    session: AsyncSession,
    request: CreateSupportTicketInput,
) -> TicketResult:
    """Create a support ticket after verifying the customer exists."""

    customer = await session.get(User, request.customer_id)
    if customer is None:
        raise ToolNotFoundError(f"Customer was not found: {request.customer_id}")

    ticket = Ticket(
        customer_id=customer.id,
        subject=request.subject,
        description=request.description,
        priority=request.priority,
        status=TicketStatus.OPEN,
    )
    session.add(ticket)
    await session.commit()
    await session.refresh(ticket)

    return TicketResult(
        ticket_id=ticket.id,
        status=ticket.status,
        priority=ticket.priority,
    )


async def escalate_to_human(
    session: AsyncSession,
    request: EscalateToHumanInput,
) -> TicketResult:
    """Create an urgent ticket or upgrade an existing customer ticket."""

    customer = await session.get(User, request.customer_id)
    if customer is None:
        raise ToolNotFoundError(f"Customer was not found: {request.customer_id}")

    if request.ticket_id is not None:
        ticket = await session.get(Ticket, request.ticket_id)
        if ticket is None or ticket.customer_id != customer.id:
            raise ToolNotFoundError("The escalation ticket was not found")
        ticket.priority = TicketPriority.URGENT
        ticket.status = TicketStatus.IN_PROGRESS
        ticket.description = f"{ticket.description}\n\nEscalation reason: {request.reason}"
    else:
        ticket = Ticket(
            customer_id=customer.id,
            subject="Human support escalation",
            description=request.reason,
            priority=TicketPriority.URGENT,
            status=TicketStatus.IN_PROGRESS,
        )
        session.add(ticket)

    await session.flush()
    escalation = await session.scalar(
        select(Escalation).where(Escalation.ticket_id == ticket.id)
    )
    if escalation is None:
        escalation = Escalation(
            ticket_id=ticket.id,
            customer_id=customer.id,
            reason=request.reason,
            status=EscalationStatus.OPEN,
        )
        session.add(escalation)
    else:
        escalation.reason = request.reason
        escalation.status = EscalationStatus.OPEN

    await session.commit()
    await session.refresh(ticket)
    await session.refresh(escalation)
    return TicketResult(
        ticket_id=ticket.id,
        status=ticket.status,
        priority=ticket.priority,
        escalation_id=escalation.id,
    )
