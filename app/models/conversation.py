from enum import Enum
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from app.core.utils import utc_now

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.agent import Agent
    from app.models.message import Message


class ConversationStatus(str, Enum):
    BOT_ACTIVE = "BOT_ACTIVE"
    PENDING_AGENT = "PENDING_AGENT"
    HUMAN_ACTIVE = "HUMAN_ACTIVE"
    CLOSED = "CLOSED"


class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True, nullable=False)
    assigned_agent_id: Optional[int] = Field(
        default=None, foreign_key="agents.id", index=True
    )
    status: ConversationStatus = Field(
        default=ConversationStatus.BOT_ACTIVE,
        nullable=False
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        nullable=False
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        nullable=False
    )

    # Relationships
    user: Optional["User"] = Relationship(back_populates="conversations")
    assigned_agent: Optional["Agent"] = Relationship(back_populates="conversations")
    messages: List["Message"] = Relationship(back_populates="conversation")
