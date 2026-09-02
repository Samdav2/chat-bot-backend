from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class QuickResponseCreateSchema(BaseModel):
    title: str = Field(..., min_length=1, max_length=150, description="Short title or label for snippet")
    content: str = Field(..., min_length=1, description="Message text content")


class QuickResponseReadSchema(BaseModel):
    id: int
    title: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
