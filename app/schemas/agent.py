from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict


class AgentLoginSchema(BaseModel):
    email: EmailStr
    password: str


class AgentCreateSchema(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    telegram_chat_id: Optional[str] = None
    telegram_username: Optional[str] = None


class AgentUpdateSchema(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    telegram_username: Optional[str] = None


class AgentReadSchema(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    is_online: bool
    telegram_chat_id: Optional[str] = None
    telegram_username: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"
    agent: AgentReadSchema
