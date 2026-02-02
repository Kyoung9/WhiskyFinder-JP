import time
from typing import Any


class TTLCache:
    def __init__(self, ttl_seconds: int = 86400):
        self.ttl = ttl_seconds
        self.store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any:
        item = self.store.get(key)
        if not item:
            return None
        expires_at, value = item
        if expires_at < time.time():
            self.store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self.store[key] = (time.time() + self.ttl, value)
