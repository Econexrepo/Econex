"""
Econex Backend – Server-Side Cache
TTLCache with 512 entries, 1-hour TTL.
Decorator works with both sync and async endpoint functions.
"""

import asyncio
from functools import wraps

from cachetools import TTLCache

# Shared cache: 512 entries max, 1-hour TTL
_cache: TTLCache = TTLCache(maxsize=512, ttl=3600)


def _build_key(func, kwargs: dict) -> str:
    """Build a deterministic cache key from function identity + relevant kwargs."""
    key_parts = [func.__module__, func.__qualname__]
    for k, v in sorted(kwargs.items()):
        if k not in ("db", "_", "conn"):  # skip DB session, auth user, raw connection
            key_parts.append(f"{k}={v}")
    return ":".join(key_parts)


def cached_endpoint(func):
    """Cache the return value of an endpoint function for 1 hour.
    Only successful results are cached. Exceptions propagate uncached.
    Works with both sync (def) and async (async def) endpoints."""

    if asyncio.iscoroutinefunction(func):

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            key = _build_key(func, kwargs)
            if key in _cache:
                return _cache[key]
            result = await func(*args, **kwargs)
            _cache[key] = result
            return result

        return async_wrapper
    else:

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            key = _build_key(func, kwargs)
            if key in _cache:
                return _cache[key]
            result = func(*args, **kwargs)
            _cache[key] = result
            return result

        return sync_wrapper


def clear_cache():
    """Clear all cached data. Call on data refresh if needed."""
    _cache.clear()


def get_cache() -> TTLCache:
    """Access the cache directly (e.g. for preloading stats)."""
    return _cache
