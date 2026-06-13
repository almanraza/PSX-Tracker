# services/cache.py
# Simple in-memory TTL cache.
# Stores scraped PSX data so we don't hammer the website on every request.

import time
from typing import Any, Optional


class TTLCache:
    def __init__(self, ttl_seconds: int = 300):
        self.ttl = ttl_seconds
        self._store: dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Optional[Any]:
        if key not in self._store:
            return None
        value, stored_at = self._store[key]
        if time.time() - stored_at > self.ttl:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (value, time.time())

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        self._store.clear()


# Shared cache: stock data cached for 5 minutes
stock_cache = TTLCache(ttl_seconds=300)
