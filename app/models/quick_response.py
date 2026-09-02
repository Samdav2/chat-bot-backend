from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field
from app.core.utils import utc_now


class QuickResponse(SQLModel, table=True):
    __tablename__ = "quick_responses"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(nullable=False, index=True)
    content: str = Field(nullable=False)
    created_at: datetime = Field(
        default_factory=utc_now,
        nullable=False
    )
