"""Async Redis client foundation (PROJECT.md section 26).

Redis backs queues, locks, rate limiting, and other short-lived/coordination
state. It is never the source of truth for durable task state -- that is
PostgreSQL (AGENTS.md rule 66).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

import redis.asyncio as redis

from app.config import get_settings


@lru_cache
def get_redis_pool() -> redis.ConnectionPool:
    settings = get_settings()
    return redis.ConnectionPool.from_url(
        settings.redis.url, max_connections=settings.redis.max_connections
    )


async def get_redis_client() -> AsyncIterator[redis.Redis]:
    """FastAPI dependency yielding a pooled Redis client."""

    client = redis.Redis(connection_pool=get_redis_pool())
    try:
        yield client
    finally:
        await client.aclose()
