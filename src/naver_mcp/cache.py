from __future__ import annotations

import copy
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional


@dataclass
class _CacheEntry:
    value: Any
    expires_at: float


class TTLCache:
    def __init__(
        self,
        default_ttl_sec: int = 300,
        now_fn: Optional[Callable[[], float]] = None,
    ) -> None:
        self.default_ttl_sec = default_ttl_sec
        self._now_fn = now_fn or time.monotonic
        self._store: dict[str, _CacheEntry] = {}

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.expires_at <= self._now_fn():
            self._store.pop(key, None)
            return None
        return copy.deepcopy(entry.value)

    def set(self, key: str, value: Any, ttl_sec: Optional[int] = None) -> None:
        ttl = ttl_sec if ttl_sec is not None else self.default_ttl_sec
        self._store[key] = _CacheEntry(
            value=copy.deepcopy(value),
            expires_at=self._now_fn() + ttl,
        )

    def clear(self) -> None:
        self._store.clear()
