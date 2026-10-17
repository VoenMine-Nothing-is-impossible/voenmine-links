"""Redis: кэш горячих ссылок + атомарные счётчики."""
import json

import redis.asyncio as aioredis

from .config import settings

_pool = None


def get_redis():
    global _pool
    if _pool is None:
        _pool = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _pool


CACHE_TTL = 60


async def get_cached_link(code: str) -> dict | None:
    try:
        r = get_redis()
        raw = await r.get(f"link:{code}")
        return json.loads(raw) if raw else None
    except Exception:
        return None


async def set_cached_link(code: str, payload: dict, ttl: int = CACHE_TTL):
    try:
        r = get_redis()
        await r.setex(f"link:{code}", ttl, json.dumps(payload, default=str))
    except Exception:
        pass


async def invalidate_link(code: str):
    try:
        r = get_redis()
        await r.delete(f"link:{code}")
    except Exception:
        pass


async def incr_click(code: str) -> int:
    """Атомарный инкремент счётчика переходов."""
    try:
        r = get_redis()
        return int(await r.incr(f"clicks:{code}"))
    except Exception:
        return -1
