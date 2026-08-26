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


class AgentReadSchema(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    is_online: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"
    agent: AgentReadSchema
