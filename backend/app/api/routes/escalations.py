"""Human escalation API endpoints."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agent.tools import (
    EscalateToHumanInput,
    ToolNotFoundError,
    escalate_to_human,
)
from backend.app.db.models import Escalation, EscalationStatus
from backend.app.db.session import get_db_session


router = APIRouter(prefix="/escalations", tags=["escalations"])


class EscalationCreateRequest(BaseModel):
    """Request body for opening or refreshing a human escalation."""

    customer_id: UUID
    reason: str = Field(min_length=1, max_length=10000)
    ticket_id: UUID | None = None


class EscalationResponse(BaseModel):
    """Public escalation representation."""

    id: UUID
    ticket_id: UUID
    customer_id: UUID
    assigned_agent_id: UUID | None
    reason: str
    status: EscalationStatus
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None

    model_config = {"from_attributes": True}


@router.post("", response_model=EscalationResponse, status_code=status.HTTP_201_CREATED)
async def create_escalation(
    request: EscalationCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> EscalationResponse:
    """Create or refresh an urgent human-support escalation."""

    try:
        result = await escalate_to_human(
            session,
            EscalateToHumanInput(
                customer_id=request.customer_id,
                reason=request.reason,
                ticket_id=request.ticket_id,
            ),
        )
    except ToolNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    escalation = await session.get(Escalation, result.escalation_id)
    if escalation is None:
        raise HTTPException(status_code=500, detail="Escalation was not persisted")
    return EscalationResponse.model_validate(escalation)


@router.get("/{escalation_id}", response_model=EscalationResponse)
async def get_escalation(
    escalation_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> EscalationResponse:
    """Return the current state of an escalation."""

    escalation = await session.scalar(
        select(Escalation).where(Escalation.id == escalation_id)
    )
    if escalation is None:
        raise HTTPException(status_code=404, detail="Escalation not found")
    return EscalationResponse.model_validate(escalation)
