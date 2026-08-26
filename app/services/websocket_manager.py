import json
import logging
import asyncio
from typing import Dict, Set, Optional
from fastapi import WebSocket
from redis.asyncio import Redis
from app.core.redis import get_redis

logger = logging.getLogger("service.websocket")


class WebSocketManager:
    """
    Async Realtime WebSocket Connection Manager & Redis PubSub relay.
    Manages active dashboard agent sockets per conversation and broadcasts live messages.
    """

    def __init__(self):
        # Maps conversation_id -> set of WebSocket connections
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, conversation_id: int, websocket: WebSocket):
        """Accept WebSocket connection and register in pool."""
        await websocket.accept()
        if conversation_id not in self.active_connections:
            self.active_connections[conversation_id] = set()
        self.active_connections[conversation_id].add(websocket)
        logger.info(f"WebSocket connected for conversation {conversation_id}")

    def disconnect(self, conversation_id: int, websocket: WebSocket):
        """Remove WebSocket connection from active pool."""
        if conversation_id in self.active_connections:
            self.active_connections[conversation_id].discard(websocket)
            if not self.active_connections[conversation_id]:
                del self.active_connections[conversation_id]
        logger.info(f"WebSocket disconnected for conversation {conversation_id}")

    async def broadcast_to_conversation(
        self, conversation_id: int, message_payload: dict
    ):
        """Broadcast payload to all open WebSockets subscribed to a conversation ID."""
        if conversation_id in self.active_connections:
            dead_sockets = set()
            json_payload = json.dumps(message_payload)
            for connection in self.active_connections[conversation_id]:
                try:
                    await connection.send_text(json_payload)
                except Exception as e:
                    logger.error(f"Error sending WebSocket message: {e}")
                    dead_sockets.add(connection)
            
            for dead in dead_sockets:
                self.disconnect(conversation_id, dead)

    async def publish_to_redis(self, conversation_id: int, message_payload: dict):
        """Publish chat event to Redis Pub/Sub channel for multi-node agent sync."""
        try:
            redis_client: Redis = await get_redis()
            channel_name = f"chat_channel:{conversation_id}"
            await redis_client.publish(channel_name, json.dumps(message_payload))
        except Exception as e:
            logger.error(f"Error publishing to Redis channel chat_channel:{conversation_id}: {e}")


# Singleton instance
ws_manager = WebSocketManager()
