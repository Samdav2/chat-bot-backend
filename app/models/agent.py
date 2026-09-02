from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from app.core.utils import utc_now

if TYPE_CHECKING:
    from app.models.conversation import Conversation


class Agent(SQLModel, table=True):
    __tablename__ = "agents"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, nullable=False, max_length=255)
    hashed_password: str = Field(nullable=False, max_length=255)
    full_name: str = Field(nullable=False, max_length=255)
    is_online: bool = Field(default=False, nullable=False)
    telegram_chat_id: Optional[str] = Field(default=None, nullable=True, max_length=255)
    telegram_username: Optional[str] = Field(default=None, nullable=True, max_length=255)
    created_at: datetime = Field(
        default_factory=utc_now,
        nullable=False
    )

    # Relationships
    conversations: List["Conversation"] = Relationship(back_populates="assigned_agent")
