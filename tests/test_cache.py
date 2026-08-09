from __future__ import annotations

import sys
import unittest
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from naver_mcp.cache import MAX_CACHE_TTL_SEC, TTLCache


class TTLCacheTest(unittest.TestCase):
    def test_set_prunes_expired_entries_that_were_not_read(self) -> None:
        now = [0.0]
        cache = TTLCache(default_ttl_sec=10, now_fn=lambda: now[0])
        cache.set("expired", {"value": 1})

        now[0] = 11.0
        cache.set("current", {"value": 2})

        self.assertEqual(cache.size, 1)
        self.assertIsNone(cache.get("expired"))
        self.assertEqual(cache.get("current"), {"value": 2})

    def test_capacity_evicts_least_recently_used_entry(self) -> None:
        cache = TTLCache(default_ttl_sec=60, max_entries=2)
        cache.set("first", 1)
        cache.set("second", 2)
        self.assertEqual(cache.get("first"), 1)

        cache.set("third", 3)

        self.assertEqual(cache.get("first"), 1)
        self.assertIsNone(cache.get("second"))
        self.assertEqual(cache.get("third"), 3)

    def test_non_positive_ttl_does_not_retain_entry(self) -> None:
        cache = TTLCache(default_ttl_sec=0)

        cache.set("disabled", {"value": 1})

        self.assertEqual(cache.size, 0)
        self.assertIsNone(cache.get("disabled"))

    def test_max_entries_must_be_positive_integer(self) -> None:
        for value in (0, -1, True, 1.5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                TTLCache(max_entries=value)  # type: ignore[arg-type]

    def test_default_ttl_must_be_bounded_integer(self) -> None:
        for value in (-1, True, 1.5, MAX_CACHE_TTL_SEC + 1, 10**309):
            with self.subTest(value=value), self.assertRaises(ValueError):
                TTLCache(default_ttl_sec=value)  # type: ignore[arg-type]

        cache = TTLCache(default_ttl_sec=MAX_CACHE_TTL_SEC, now_fn=lambda: 0.0)
        cache.set("maximum", "value")
        self.assertEqual(cache.get("maximum"), "value")

    def test_explicit_ttl_must_be_bounded_integer(self) -> None:
        cache = TTLCache()

        for value in (-1, True, 1.5, MAX_CACHE_TTL_SEC + 1, 10**309):
            with self.subTest(value=value), self.assertRaises(ValueError):
                cache.set("key", "value", ttl_sec=value)  # type: ignore[arg-type]

        self.assertEqual(cache.size, 0)


if __name__ == "__main__":
    unittest.main()
