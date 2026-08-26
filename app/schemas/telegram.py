from typing import Optional, Any, Dict
from pydantic import BaseModel, Field


class TelegramUserSchema(BaseModel):
    id: int
    is_bot: Optional[bool] = False
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None


class TelegramChatSchema(BaseModel):
    id: int
    type: str
    title: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class TelegramMessageSchema(BaseModel):
    message_id: int
    from_user: Optional[TelegramUserSchema] = Field(None, alias="from")
    chat: TelegramChatSchema
    date: int
    text: Optional[str] = None


class TelegramCallbackQuerySchema(BaseModel):
    id: str
    from_user: TelegramUserSchema = Field(..., alias="from")
    message: Optional[TelegramMessageSchema] = None
    data: Optional[str] = None


class TelegramUpdateSchema(BaseModel):
    update_id: int
    message: Optional[TelegramMessageSchema] = None
    callback_query: Optional[TelegramCallbackQuerySchema] = None
