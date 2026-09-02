from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, Column, BigInteger
from app.core.utils import utc_now

if TYPE_CHECKING:
    from app.models.conversation import Conversation


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    telegram_id: int = Field(
        sa_column=Column(BigInteger, unique=True, index=True, nullable=False)
    )
    username: Optional[str] = Field(default=None, max_length=255)
    first_name: Optional[str] = Field(default=None, max_length=255)
    last_name: Optional[str] = Field(default=None, max_length=255)
    created_at: datetime = Field(
        default_factory=utc_now,
        nullable=False
    )

    # Relationships
    conversations: List["Conversation"] = Relationship(back_populates="user")
