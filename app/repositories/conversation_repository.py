from typing import Optional, Sequence
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.utils import utc_now
from app.models.conversation import Conversation, ConversationStatus
from app.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    """Async Repository for Conversation entity operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Conversation, session)

    async def get_active_by_user_id(self, user_id: int) -> Optional[Conversation]:
        """Get currently open/active conversation for a given user ID."""
        statement = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .where(Conversation.status != ConversationStatus.CLOSED)
            .order_by(Conversation.updated_at.desc())
        )
        result = await self.session.exec(statement)
        return result.first()

    async def get_by_status(
        self, status: Optional[ConversationStatus] = None, skip: int = 0, limit: int = 50
    ) -> Sequence[Conversation]:
        """List conversations filtered by status with relationships preloaded."""
        statement = select(Conversation).options(
            selectinload(Conversation.user),
            selectinload(Conversation.assigned_agent)
        )
        if status:
            statement = statement.where(Conversation.status == status)
        
        statement = statement.order_by(Conversation.updated_at.desc()).offset(skip).limit(limit)
        result = await self.session.exec(statement)
        return result.all()

    async def get_with_details(self, conversation_id: int) -> Optional[Conversation]:
        """Fetch conversation with user, agent, and messages eagerly loaded."""
        statement = (
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(
                selectinload(Conversation.user),
                selectinload(Conversation.assigned_agent),
                selectinload(Conversation.messages)
            )
        )
        result = await self.session.exec(statement)
        return result.first()

    async def assign_agent(
        self, conversation_id: int, agent_id: int
    ) -> Optional[Conversation]:
        """Assign support agent to ticket and transition to HUMAN_ACTIVE."""
        conversation = await self.get_by_id(conversation_id)
        if conversation:
            conversation.assigned_agent_id = agent_id
            conversation.status = ConversationStatus.HUMAN_ACTIVE
            conversation.updated_at = utc_now()
            return await self.update(conversation)
        return None

    async def update_status(
        self, conversation_id: int, status: ConversationStatus
    ) -> Optional[Conversation]:
        """Update conversation status."""
        conversation = await self.get_by_id(conversation_id)
        if conversation:
            conversation.status = status
            conversation.updated_at = utc_now()
            return await self.update(conversation)
        return None
