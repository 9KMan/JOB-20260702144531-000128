"""Async cache abstraction backed by Redis with an in-memory fallback."""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Optional

from src.core.config import settings


class CacheClient:
    """Async get/set cache; falls back to a dict when Redis is unavailable."""

    def __init__(self) -> None:
        self._redis: Any = None
        self._memory: dict[str, tuple[float, Any]] = {}
        self._lock = asyncio.Lock()
        self._connect()

    def _connect(self) -> None:
        try:
            import redis.asyncio as redis_async  # type: ignore

            self._redis = redis_async.from_url(settings.REDIS_URL, decode_responses=True)
        except Exception:  # pragma: no cover
            self._redis = None

    async def get(self, key: str) -> Optional[Any]:
        if self._redis is not None:
            try:
                value = await self._redis.get(key)
                if value is None:
                    return None
                return json.loads(value)
            except Exception:
                # Fall through to memory cache
                self._redis = None

        async with self._lock:
            entry = self._memory.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if expires_at and expires_at < time.time():
                del self._memory[key]
                return None
            return value

    async def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        payload = json.dumps(value, default=str)
        if self._redis is not None:
            try:
                await self._redis.set(key, payload, ex=ttl_seconds)
                return
            except Exception:
                self._redis = None

        async with self._lock:
            self._memory[key] = (time.time() + ttl_seconds, value)

    async def delete(self, key: str) -> None:
        if self._redis is not None:
            try:
                await self._redis.delete(key)
                return
            except Exception:
                self._redis = None
        async with self._lock:
            self._memory.pop(key, None)

    async def ping(self) -> bool:
        if self._redis is not None:
            try:
                return bool(await self._redis.ping())
            except Exception:
                return False
        return True


_singleton: Optional[CacheClient] = None


def get_cache() -> CacheClient:
    global _singleton
    if _singleton is None:
        _singleton = CacheClient()
    return _singleton
