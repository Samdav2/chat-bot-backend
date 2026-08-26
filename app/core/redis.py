import logging
from typing import Optional
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger(__name__)

class RedisClient:
    _redis: Optional[aioredis.Redis] = None

    @classmethod
    async def get_client(cls) -> aioredis.Redis:
        """Get or initialize async Redis client."""
        if cls._redis is None:
            logger.info("Initializing Redis connection...")
            cls._redis = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=3
            )
        return cls._redis

    @classmethod
    async def close(cls) -> None:
        """Close Redis connection pool."""
        if cls._redis is not None:
            await cls._redis.close()
            cls._redis = None
            logger.info("Redis connection closed.")


async def get_redis() -> aioredis.Redis:
    """Dependency injection for Redis client."""
    return await RedisClient.get_client()
