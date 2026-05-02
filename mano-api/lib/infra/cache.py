"""
Cache backend with Redis primary and in-memory fallback.

Every caller interacts with the same ``CacheBackend`` interface:

    cache = get_cache()
    await cache.get("weather:Colombo")
    await cache.set("weather:Colombo", payload, ttl=21_600)

When ``settings.redis_url`` is set and ``redis.asyncio`` is importable, we
delegate to Redis. Otherwise we fall back to a per-process TTL dict. The
fallback is *not* a Redis feature — it's a guarantee that the app boots with
zero operational dependencies in development.

The backend is deliberately boring: JSON-serialisable payloads only, no
pickling, no cluster awareness. Complex objects should serialise themselves
before calling ``set``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, Optional, Tuple

from core.config import settings

logger = logging.getLogger(__name__)


# ─── abstract-ish base ──────────────────────────────────────────────────────

class CacheBackend:
    """Uniform async cache interface. Subclasses implement get/set/delete/close."""

    backend_name: str = "noop"

    async def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        raise NotImplementedError

    async def delete(self, key: str) -> None:
        raise NotImplementedError

    async def clear(self) -> None:
        """Clear all keys. Only used in tests."""
        raise NotImplementedError

    async def ping(self) -> bool:
        """Return True if the backend is reachable. Used by /health."""
        return True

    async def close(self) -> None:  # pragma: no cover — trivial
        pass


# ─── in-memory TTL fallback ────────────────────────────────────────────────

class InMemoryCache(CacheBackend):
    """Thread-safe (via asyncio.Lock) TTL dict suitable for dev / tests."""

    backend_name = "memory"

    def __init__(self) -> None:
        self._store: Dict[str, Tuple[float, Any]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            expires_at, value = entry
            if expires_at and expires_at < time.time():
                self._store.pop(key, None)
                return None
            return value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        expires_at = time.time() + ttl if ttl and ttl > 0 else 0.0
        async with self._lock:
            self._store[key] = (expires_at, value)

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()

    async def ping(self) -> bool:
        return True


# ─── Redis backend ─────────────────────────────────────────────────────────

class RedisCache(CacheBackend):
    """Redis 5+ async client wrapper. Values are JSON-encoded."""

    backend_name = "redis"

    def __init__(self, url: str) -> None:
        # Imported lazily so the rest of the app boots even without the dep.
        import redis.asyncio as redis_async  # type: ignore

        self._client = redis_async.from_url(
            url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=2.0,
            socket_timeout=2.0,
        )
        self._url = url

    async def get(self, key: str) -> Optional[Any]:
        try:
            raw = await self._client.get(key)
        except Exception as exc:  # network blip, malformed key etc.
            logger.warning("redis_get_failed", extra={"key": key, "error": str(exc)})
            return None
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Non-JSON entry (e.g. written by another service). Return raw.
            return raw

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        try:
            payload = json.dumps(value, default=str)
        except (TypeError, ValueError) as exc:
            logger.error("redis_set_encode_failed", extra={"key": key, "error": str(exc)})
            return
        try:
            if ttl and ttl > 0:
                await self._client.set(key, payload, ex=ttl)
            else:
                await self._client.set(key, payload)
        except Exception as exc:
            logger.warning("redis_set_failed", extra={"key": key, "error": str(exc)})

    async def delete(self, key: str) -> None:
        try:
            await self._client.delete(key)
        except Exception as exc:
            logger.warning("redis_delete_failed", extra={"key": key, "error": str(exc)})

    async def clear(self) -> None:
        try:
            await self._client.flushdb()
        except Exception as exc:
            logger.warning("redis_flushdb_failed", extra={"error": str(exc)})

    async def ping(self) -> bool:
        try:
            return bool(await self._client.ping())
        except Exception:
            return False

    async def close(self) -> None:
        try:
            await self._client.aclose()
        except Exception:  # pragma: no cover — best effort
            pass


# ─── Factory / singleton ───────────────────────────────────────────────────

_cache: Optional[CacheBackend] = None


def get_cache() -> CacheBackend:
    """Return the process-wide cache backend, constructing it on first call."""
    global _cache
    if _cache is not None:
        return _cache

    if settings.has_redis:
        try:
            _cache = RedisCache(settings.redis_url)  # type: ignore[arg-type]
            logger.info("cache_backend_selected", extra={"backend": "redis"})
            return _cache
        except ImportError:
            logger.warning(
                "cache_redis_lib_missing",
                extra={"hint": "pip install redis>=5.0 to enable Redis caching"},
            )
        except Exception as exc:
            logger.warning(
                "cache_redis_init_failed",
                extra={"error": str(exc), "fallback": "memory"},
            )

    _cache = InMemoryCache()
    logger.info("cache_backend_selected", extra={"backend": "memory"})
    return _cache


async def reset_cache_for_tests() -> None:
    """Drop the singleton and clear contents. Only used in the test suite."""
    global _cache
    if _cache is not None:
        await _cache.close()
    _cache = None
