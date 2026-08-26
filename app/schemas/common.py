from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel

T = TypeVar("T")


class ResponseSchema(BaseModel, Generic[T]):
    success: bool = True
    message: str = "Operation completed successfully"
    data: Optional[T] = None


class MessageWebSocketPayload(BaseModel):
    content: str
    senderRole: str  # USER, AGENT, BOT
    senderId: int
    timestamp: Optional[str] = None
