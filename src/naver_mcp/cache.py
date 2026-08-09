from __future__ import annotations

import copy
import time
from collections import OrderedDict
from dataclasses import dataclass
from threading import RLock
from typing import Any, Callable, Optional

DEFAULT_CACHE_MAX_ENTRIES = 1024
MAX_CACHE_TTL_SEC = 31_536_000


def _validate_ttl(ttl_sec: object) -> int:
    if isinstance(ttl_sec, bool) or not isinstance(ttl_sec, int):
        raise ValueError("ttl_sec must be an integer between 0 and 31536000")
    if not 0 <= ttl_sec <= MAX_CACHE_TTL_SEC:
        raise ValueError("ttl_sec must be an integer between 0 and 31536000")
    return ttl_sec


@dataclass
class _CacheEntry:
    value: Any
    expires_at: float


class TTLCache:
    def __init__(
        self,
        default_ttl_sec: int = 300,
        now_fn: Optional[Callable[[], float]] = None,
        max_entries: int = DEFAULT_CACHE_MAX_ENTRIES,
    ) -> None:
        if isinstance(max_entries, bool) or not isinstance(max_entries, int):
            raise ValueError("max_entries must be a positive integer")
        if max_entries <= 0:
            raise ValueError("max_entries must be a positive integer")
        self.default_ttl_sec = _validate_ttl(default_ttl_sec)
        self._now_fn = now_fn or time.monotonic
        self._max_entries = max_entries
        self._store: OrderedDict[str, _CacheEntry] = OrderedDict()
        self._lock = RLock()

    def _prune_expired(self, now: float) -> None:
        expired_keys = [
            key for key, entry in self._store.items() if entry.expires_at <= now
        ]
        for key in expired_keys:
            self._store.pop(key, None)

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if entry.expires_at <= self._now_fn():
                self._store.pop(key, None)
                return None
            self._store.move_to_end(key)
            return copy.deepcopy(entry.value)

    def set(self, key: str, value: Any, ttl_sec: Optional[int] = None) -> None:
        ttl = _validate_ttl(
            ttl_sec if ttl_sec is not None else self.default_ttl_sec
        )
        with self._lock:
            now = self._now_fn()
            self._prune_expired(now)
            self._store.pop(key, None)
            if ttl <= 0:
                return
            if len(self._store) >= self._max_entries:
                self._store.popitem(last=False)
            self._store[key] = _CacheEntry(
                value=copy.deepcopy(value),
                expires_at=now + ttl,
            )

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._store)
