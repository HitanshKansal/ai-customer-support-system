"""Authenticated agent chat endpoint."""

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agent.runtime import AgentRequest, AgentResponse, SupportAgent
from backend.app.api.dependencies import get_support_agent
from backend.app.api.routes.auth import get_current_user
from backend.app.db.models import User
from backend.app.db.session import get_db_session


router = APIRouter(prefix="/agent", tags=["agent"])


class ChatRequest(BaseModel):
    """Authenticated chat input."""

    message: str = Field(min_length=1, max_length=10000)
    conversation_id: UUID = Field(default_factory=uuid4)
    order_number: str | None = Field(default=None, max_length=50)
    ticket_id: UUID | None = None


@router.post("/chat", response_model=AgentResponse)
async def chat(
    request: ChatRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    agent: SupportAgent = Depends(get_support_agent),
) -> AgentResponse:
    """Route one authenticated customer message through the support agent."""

    return await agent.handle(
        session,
        AgentRequest(
            user_message=request.message,
            customer_id=user.id,
            conversation_id=request.conversation_id,
            order_number=request.order_number,
            ticket_id=request.ticket_id,
        ),
    )
