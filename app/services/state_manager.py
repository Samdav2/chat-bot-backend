import logging
from typing import Optional
from redis.asyncio import Redis
from app.core.redis import get_redis

logger = logging.getLogger("service.state_manager")


class SessionStateManager:
    """Async Redis state manager for customer Telegram session status."""

    def __init__(self, redis_client: Optional[Redis] = None):
        self._redis = redis_client

    async def _get_redis(self) -> Redis:
        if self._redis is None:
            self._redis = await get_redis()
        return self._redis

    async def get_user_state(self, telegram_id: int) -> str:
        """Fetch active session state for a given Telegram customer ID."""
        try:
            client = await self._get_redis()
            state = await client.get(f"user_state:{telegram_id}")
            return state if state else "BOT_ACTIVE"
        except Exception as e:
            logger.error(f"Error fetching Redis user state for {telegram_id}: {e}")
            return "BOT_ACTIVE"

    async def set_user_state(self, telegram_id: int, state: str, ttl: int = 86400):
        """Set customer session state in Redis (States: BOT_ACTIVE, PENDING_AGENT, HUMAN_ACTIVE, CLOSED)."""
        try:
            client = await self._get_redis()
            await client.set(f"user_state:{telegram_id}", state, ex=ttl)
            logger.info(f"Updated user_state for {telegram_id} to '{state}'")
        except Exception as e:
            logger.error(f"Error setting Redis user state for {telegram_id}: {e}")

    async def assign_agent(self, telegram_id: int, agent_id: int, ttl: int = 86400):
        """Map assigned support agent ID to customer session in Redis."""
        try:
            client = await self._get_redis()
            await client.set(f"assigned_agent:{telegram_id}", agent_id, ex=ttl)
            logger.info(f"Assigned agent {agent_id} to Telegram customer {telegram_id}")
        except Exception as e:
            logger.error(f"Error assigning agent for {telegram_id}: {e}")

    async def get_assigned_agent(self, telegram_id: int) -> Optional[int]:
        """Fetch assigned support agent ID from Redis."""
        try:
            client = await self._get_redis()
            agent_id = await client.get(f"assigned_agent:{telegram_id}")
            return int(agent_id) if agent_id else None
        except Exception as e:
            logger.error(f"Error fetching assigned agent for {telegram_id}: {e}")
            return None

    async def clear_session(self, telegram_id: int):
        """Clear active user state and agent assignment from Redis."""
        try:
            client = await self._get_redis()
            await client.delete(f"user_state:{telegram_id}")
            await client.delete(f"assigned_agent:{telegram_id}")
            logger.info(f"Cleared session keys for customer {telegram_id}")
        except Exception as e:
            logger.error(f"Error clearing session for {telegram_id}: {e}")
