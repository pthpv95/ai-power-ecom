"""
Shared async Redis connection pool.

Used by both the API server (SSE reader) and the Arq worker (event publisher).
A single pool avoids creating a new TCP connection per request.
"""
import redis.asyncio as aioredis

from app.config import settings

# Lazy singleton — initialized on first call to get_redis()
_pool: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    """Return the shared Redis client (creates pool on first call)."""
    global _pool
    if _pool is None:
        _pool = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
        )
    return _pool


async def close_redis() -> None:
    """Graceful shutdown — call from FastAPI lifespan or worker shutdown."""
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None
