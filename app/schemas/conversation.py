from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from app.models.conversation import ConversationStatus
from app.models.message import SenderRole
from app.schemas.agent import AgentReadSchema


class MessageCreateSchema(BaseModel):
    content: str = ""
    media_url: Optional[str] = None
    media_type: Optional[str] = None
    sender_role: SenderRole = SenderRole.AGENT
    send_to_telegram: bool = True


class MessageReadSchema(BaseModel):
    id: int
    conversation_id: int
    sender_role: SenderRole
    sender_id: int
    content: str
    media_url: Optional[str] = None
    media_type: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserReadSchema(BaseModel):
    id: int
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationReadSchema(BaseModel):
    id: int
    user_id: int
    assigned_agent_id: Optional[int] = None
    status: ConversationStatus
    created_at: datetime
    updated_at: datetime
    user: Optional[UserReadSchema] = None
    assigned_agent: Optional[AgentReadSchema] = None
    latest_message: Optional[MessageReadSchema] = None

    model_config = ConfigDict(from_attributes=True)


class ConversationDetailSchema(ConversationReadSchema):
    messages: List[MessageReadSchema] = []
