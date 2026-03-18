from __future__ import annotations

import sys
import unittest
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from naver_mcp.normalize import (
    normalize_adult_query_response,
    normalize_datalab_device_trends_response,
    normalize_published_at,
    normalize_search_response,
    normalize_spell_check_response,
    strip_html,
)


class NormalizeTest(unittest.TestCase):
    def test_strip_html_removes_tags_and_unescapes_entities(self) -> None:
        self.assertEqual(strip_html("<b>Tom &amp; Jerry</b>"), "Tom & Jerry")

    def test_normalize_published_at_handles_rfc822(self) -> None:
        self.assertEqual(
            normalize_published_at("Wed, 18 Mar 2026 12:00:00 +0900"),
            "2026-03-18T12:00:00+09:00",
        )

    def test_normalize_search_response_shapes_local_items(self) -> None:
        payload = {
            "total": 1,
            "start": 1,
            "display": 5,
            "items": [
                {
                    "title": "<b>판교 맛집</b>",
                    "link": "https://example.com/local",
                    "description": "직장인 추천",
                    "category": "한식",
                    "address": "성남시 분당구",
                    "roadAddress": "분당구 판교역로",
                    "telephone": "031-000-0000",
                    "mapx": "1271234567",
                    "mapy": "371234567",
                }
            ],
        }

        result = normalize_search_response(
            "판교 맛집",
            "local",
            payload,
            display=5,
            start=1,
        )

        self.assertEqual(result["query"], "판교 맛집")
        self.assertEqual(result["source"], "local")
        self.assertFalse(result["meta"]["cached"])
        self.assertEqual(result["items"][0]["name"], "판교 맛집")
        self.assertEqual(result["items"][0]["category"], "한식")

    def test_normalize_spell_check_response_uses_query_when_no_change(self) -> None:
        result = normalize_spell_check_response("pangyo", {"errata": ""})

        self.assertEqual(result["corrected_query"], "pangyo")
        self.assertFalse(result["changed"])
        self.assertFalse(result["meta"]["cached"])

    def test_normalize_adult_query_response_parses_nested_item(self) -> None:
        payload = {"result": {"item": [{"adult": "1"}]}}

        result = normalize_adult_query_response("query", payload)

        self.assertTrue(result["is_adult"])

    def test_normalize_datalab_device_response_preserves_group(self) -> None:
        payload = {
            "startDate": "2026-03-01",
            "endDate": "2026-03-18",
            "timeUnit": "date",
            "results": [
                {
                    "title": "50000000",
                    "category": ["50000000"],
                    "data": [{"period": "2026-03-01", "group": "mo", "ratio": 81.1}],
                }
            ],
        }

        result = normalize_datalab_device_trends_response(payload)

        self.assertEqual(result["results"][0]["category"], ["50000000"])
        self.assertEqual(result["results"][0]["data"][0]["group"], "mo")
        self.assertEqual(result["meta"]["time_unit"], "date")


if __name__ == "__main__":
    unittest.main()
