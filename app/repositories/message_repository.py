from typing import Sequence, Optional
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.message import Message, SenderRole
from app.repositories.base import BaseRepository


class MessageRepository(BaseRepository[Message]):
    """Async Repository for Chat Message history operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Message, session)

    async def get_by_conversation_id(
        self, conversation_id: int, skip: int = 0, limit: int = 100
    ) -> Sequence[Message]:
        """Fetch all messages in a conversation ordered chronologically."""
        statement = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.exec(statement)
        return result.all()

    async def get_latest_message(self, conversation_id: int) -> Optional[Message]:
        """Fetch the most recent message in a conversation."""
        statement = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
        )
        result = await self.session.exec(statement)
        return result.first()

    async def add_message(
        self,
        conversation_id: int,
        sender_role: SenderRole,
        sender_id: int,
        content: str,
        media_url: Optional[str] = None,
        media_type: Optional[str] = None,
    ) -> Message:
        """Create and store a chat message entry."""
        message = Message(
            conversation_id=conversation_id,
            sender_role=sender_role,
            sender_id=sender_id,
            content=content,
            media_url=media_url,
            media_type=media_type,
        )
        return await self.create(message)
