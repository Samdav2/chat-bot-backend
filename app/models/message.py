from enum import Enum
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, Column, BigInteger
from app.core.utils import utc_now

if TYPE_CHECKING:
    from app.models.conversation import Conversation


class SenderRole(str, Enum):
    USER = "USER"
    BOT = "BOT"
    AGENT = "AGENT"


class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int = Field(
        foreign_key="conversations.id", index=True, nullable=False
    )
    sender_role: SenderRole = Field(nullable=False)
    sender_id: int = Field(sa_column=Column(BigInteger, nullable=False))  # telegram_id or agent_id
    content: str = Field(nullable=False)
    media_url: Optional[str] = Field(default=None, nullable=True)
    media_type: Optional[str] = Field(default=None, nullable=True)
    created_at: datetime = Field(
        default_factory=utc_now,
        nullable=False
    )

    # Relationship
    conversation: Optional["Conversation"] = Relationship(back_populates="messages")
