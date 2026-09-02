from fastapi import APIRouter
from app.api.v1.endpoints import auth, telegram, conversations, websocket, quick_responses

api_v1_router = APIRouter()

api_v1_router.include_router(auth.router, prefix="/auth", tags=["Agent Auth"])
api_v1_router.include_router(telegram.router, prefix="/telegram", tags=["Telegram Webhook"])
api_v1_router.include_router(conversations.router, prefix="/conversations", tags=["Conversations REST"])
api_v1_router.include_router(quick_responses.router, prefix="/quick-responses", tags=["Quick Responses"])
api_v1_router.include_router(websocket.router, tags=["Realtime WebSockets"])
