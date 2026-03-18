"""
GridGuard AI — Redis Client & Cache Helpers
TTL-based caching for grid workability scores and OTP sessions.
"""

import json
from typing import Any

import redis.asyncio as redis

from app.config import get_settings

settings = get_settings()

# Async Redis connection pool
redis_pool = redis.ConnectionPool.from_url(
    settings.redis_url,
    decode_responses=True,
    max_connections=50,
)

redis_client = redis.Redis(connection_pool=redis_pool)


# ── Cache Key Patterns ──
GRID_CACHE_KEY = "grid:{h3_cell}"
OTP_CACHE_KEY = "otp:{session_token}"
PARTNER_CACHE_KEY = "partner:{partner_id}"

# ── TTLs ──
GRID_CACHE_TTL = 900        # 15 minutes
OTP_TTL = 300                # 5 minutes
PARTNER_CACHE_TTL = 3600     # 1 hour


async def get_cached_workability(h3_cell: str) -> dict | None:
    """Get cached workability score for an H3 cell."""
    key = GRID_CACHE_KEY.format(h3_cell=h3_cell)
    data = await redis_client.get(key)
    if data:
        return json.loads(data)
    return None


async def set_cached_workability(h3_cell: str, data: dict, ttl: int = GRID_CACHE_TTL) -> None:
    """Cache workability score for an H3 cell."""
    key = GRID_CACHE_KEY.format(h3_cell=h3_cell)
    await redis_client.setex(key, ttl, json.dumps(data, default=str))


async def invalidate_workability_cache(h3_cell: str) -> None:
    """Invalidate cached workability score for an H3 cell."""
    key = GRID_CACHE_KEY.format(h3_cell=h3_cell)
    await redis_client.delete(key)


async def store_otp(session_token: str, otp_code: str, partner_id: str) -> None:
    """Store OTP in Redis with 5-minute TTL."""
    key = OTP_CACHE_KEY.format(session_token=session_token)
    data = json.dumps({"otp_code": otp_code, "partner_id": partner_id})
    await redis_client.setex(key, OTP_TTL, data)


async def verify_otp(session_token: str, otp_code: str) -> dict | None:
    """Verify OTP from Redis. Returns partner data if valid, None otherwise."""
    key = OTP_CACHE_KEY.format(session_token=session_token)
    data = await redis_client.get(key)
    if not data:
        return None
    parsed = json.loads(data)
    if parsed["otp_code"] == otp_code:
        await redis_client.delete(key)  # One-time use
        return parsed
    return None


async def cache_set(key: str, value: Any, ttl: int = 3600) -> None:
    """Generic cache set."""
    await redis_client.setex(key, ttl, json.dumps(value, default=str))


async def cache_get(key: str) -> Any | None:
    """Generic cache get."""
    data = await redis_client.get(key)
    if data:
        return json.loads(data)
    return None


async def cache_delete(key: str) -> None:
    """Generic cache delete."""
    await redis_client.delete(key)
