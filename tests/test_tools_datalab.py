from __future__ import annotations

import sys
import unittest
from collections.abc import Mapping
from pathlib import Path
from typing import Any

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from naver_mcp.cache import TTLCache
from naver_mcp.errors import ValidationError
from naver_mcp.models import (
    DataLabSearchTrendsRequest,
    DataLabShoppingCategoryTrendsRequest,
    DataLabShoppingDeviceTrendsRequest,
)
from naver_mcp.tools_datalab import DataLabTools


class FakeDataLabClient:
    def __init__(self) -> None:
        self.calls = {
            "search_trends": 0,
            "shopping_category": 0,
            "shopping_device": 0,
        }

    def datalab_search_trends(
        self,
        request: DataLabSearchTrendsRequest,
    ) -> Mapping[str, Any]:
        self.calls["search_trends"] += 1
        return {
            "startDate": request.start_date,
            "endDate": request.end_date,
            "timeUnit": request.time_unit,
            "results": [
                {
                    "title": request.keyword_groups[0].group_name,
                    "keywords": request.keyword_groups[0].keywords,
                    "data": [{"period": "2026-03-01", "ratio": 78.1}],
                }
            ],
        }

    def datalab_shopping_category_trends(
        self,
        request: DataLabShoppingCategoryTrendsRequest,
    ) -> Mapping[str, Any]:
        self.calls["shopping_category"] += 1
        return {
            "startDate": request.start_date,
            "endDate": request.end_date,
            "timeUnit": request.time_unit,
            "results": [
                {
                    "title": request.categories[0].name,
                    "category": request.categories[0].params,
                    "data": [{"period": "2026-03-01", "ratio": 51.2}],
                }
            ],
        }

    def datalab_shopping_device_trends(
        self,
        request: DataLabShoppingDeviceTrendsRequest,
    ) -> Mapping[str, Any]:
        self.calls["shopping_device"] += 1
        return {
            "startDate": request.start_date,
            "endDate": request.end_date,
            "timeUnit": request.time_unit,
            "results": [
                {
                    "title": request.category,
                    "category": [request.category],
                    "data": [
                        {"period": "2026-03-01", "group": "mo", "ratio": 81.1},
                        {"period": "2026-03-01", "group": "pc", "ratio": 18.9},
                    ],
                }
            ],
        }


class DataLabToolsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = FakeDataLabClient()
        self.tools = DataLabTools(self.client, cache=TTLCache(default_ttl_sec=1800))

    def test_datalab_search_trends_returns_normalized_results(self) -> None:
        result = self.tools.datalab_search_trends(
            start_date="2026-03-01",
            end_date="2026-03-18",
            time_unit="date",
            keyword_groups=[
                {
                    "group_name": "pangyo",
                    "keywords": ["pangyo restaurants", "pangyo cafe"],
                }
            ],
        )

        self.assertEqual(result["results"][0]["title"], "pangyo")
        self.assertEqual(result["results"][0]["data"][0]["ratio"], 78.1)
        self.assertEqual(result["meta"]["start_date"], "2026-03-01")
        self.assertFalse(result["meta"]["cached"])

    def test_datalab_shopping_category_trends_returns_category_data(self) -> None:
        result = self.tools.datalab_shopping_category_trends(
            start_date="2026-03-01",
            end_date="2026-03-18",
            time_unit="week",
            categories=[{"name": "패션의류", "params": ["50000000"]}],
            device="pc",
            gender="f",
            ages=["20", "30"],
        )

        self.assertEqual(result["results"][0]["title"], "패션의류")
        self.assertEqual(result["results"][0]["category"], ["50000000"])
        self.assertEqual(result["results"][0]["data"][0]["ratio"], 51.2)

    def test_datalab_shopping_device_trends_returns_grouped_points(self) -> None:
        result = self.tools.datalab_shopping_device_trends(
            start_date="2026-03-01",
            end_date="2026-03-18",
            time_unit="date",
            category="50000000",
            gender="f",
            ages=["20", "30"],
        )

        self.assertEqual(result["results"][0]["title"], "50000000")
        self.assertEqual(result["results"][0]["data"][0]["group"], "mo")
        self.assertEqual(result["results"][0]["data"][1]["group"], "pc")

    def test_datalab_search_trends_validates_keyword_groups(self) -> None:
        with self.assertRaises(ValidationError):
            self.tools.datalab_search_trends(
                start_date="2026-03-01",
                end_date="2026-03-18",
                time_unit="date",
                keyword_groups=[],
            )

    def test_datalab_shopping_category_trends_validates_device(self) -> None:
        with self.assertRaises(ValidationError):
            self.tools.datalab_shopping_category_trends(
                start_date="2026-03-01",
                end_date="2026-03-18",
                time_unit="date",
                categories=[{"name": "패션의류", "params": ["50000000"]}],
                device="tablet",
            )

    def test_datalab_search_trends_uses_cache(self) -> None:
        self.tools.datalab_search_trends(
            start_date="2026-03-01",
            end_date="2026-03-18",
            time_unit="date",
            keyword_groups=[{"group_name": "pangyo", "keywords": ["pangyo restaurants"]}],
        )
        second = self.tools.datalab_search_trends(
            start_date="2026-03-01",
            end_date="2026-03-18",
            time_unit="date",
            keyword_groups=[{"group_name": "pangyo", "keywords": ["pangyo restaurants"]}],
        )

        self.assertEqual(self.client.calls["search_trends"], 1)
        self.assertTrue(second["meta"]["cached"])


if __name__ == "__main__":
    unittest.main()
