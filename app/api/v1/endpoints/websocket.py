import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session_maker
from app.services.websocket_manager import ws_manager
from app.services.conversation_service import ConversationService

router = APIRouter()
logger = logging.getLogger("api.websocket")


@router.websocket("/ws/chat/{conversation_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    conversation_id: int,
    agent_id: int = Query(..., alias="agent_id"),
):
    """
    Realtime WebSocket streaming endpoint for Next.js agent dashboard.
    Receives incoming agent messages and streams customer replies live.
    """
    await ws_manager.connect(conversation_id, websocket)
    try:
        while True:
            data_text = await websocket.receive_text()
            try:
                payload = json.loads(data_text)
                content = payload.get("content", "")
                
                if content:
                    # Open async DB session to store & dispatch message
                    async with async_session_maker() as session:
                        service = ConversationService(session)
                        await service.send_agent_message(
                            conversation_id=conversation_id,
                            agent_id=agent_id,
                            content=content,
                        )
            except Exception as ex:
                logger.error(f"Error handling WebSocket message payload: {ex}")
                await websocket.send_text(json.dumps({"error": "Invalid payload format"}))

    except WebSocketDisconnect:
        ws_manager.disconnect(conversation_id, websocket)
        logger.info(f"Agent {agent_id} disconnected from WebSocket chat {conversation_id}")
