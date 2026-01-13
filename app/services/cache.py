"""Redis caching service with async support."""

import json
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class CacheService:
    """Redis-based caching service."""

    def __init__(self):
        """Initialize cache service."""
        self.redis: Redis | None = None
        self.ttl = settings.cache_ttl

    async def connect(self) -> None:
        """Connect to Redis."""
        try:
            self.redis = Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password,
                decode_responses=True,
            )
            await self.redis.ping()
            logger.info("redis_connected", host=settings.redis_host, port=settings.redis_port)
        except RedisError as e:
            logger.error("redis_connection_failed", error=str(e))
            raise

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
            logger.info("redis_disconnected")

    async def get(self, key: str) -> dict[str, Any] | None:
        """Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        if not self.redis:
            logger.warning("cache_get_failed", reason="redis_not_connected")
            return None

        try:
            value = await self.redis.get(key)
            if value:
                logger.info("cache_hit", key=key)
                return json.loads(value)
            logger.info("cache_miss", key=key)
            return None
        except (RedisError, json.JSONDecodeError) as e:
            logger.error("cache_get_error", key=key, error=str(e))
            return None

    async def set(self, key: str, value: dict[str, Any]) -> bool:
        """Set value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            
        Returns:
            True if successful, False otherwise
        """
        if not self.redis:
            logger.warning("cache_set_failed", reason="redis_not_connected")
            return False

        try:
            await self.redis.setex(key, self.ttl, json.dumps(value))
            logger.info("cache_set", key=key, ttl=self.ttl)
            return True
        except (RedisError, TypeError) as e:
            logger.error("cache_set_error", key=key, error=str(e))
            return False

    async def is_connected(self) -> bool:
        """Check if Redis is connected.
        
        Returns:
            True if connected, False otherwise
        """
        if not self.redis:
            return False

        try:
            await self.redis.ping()
            return True
        except RedisError:
            return False


# Global cache instance
cache = CacheService()
