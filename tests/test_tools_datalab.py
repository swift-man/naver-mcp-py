from __future__ import annotations

import sys
import unittest
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Optional

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from naver_mcp.cache import TTLCache
from naver_mcp.errors import ValidationError
from naver_mcp.models import (
    DataLabSearchTrendsRequest,
    DataLabShoppingCategoryDetailRequest,
    DataLabShoppingCategoryTrendsRequest,
    DataLabShoppingKeywordDetailRequest,
    DataLabShoppingKeywordTrendsRequest,
)
from naver_mcp.tools_datalab import DataLabTools


class FakeDataLabClient:
    def __init__(self) -> None:
        self.last_search_request: Optional[DataLabSearchTrendsRequest] = None
        self.calls = {
            "search_trends": 0,
            "shopping_category": 0,
            "shopping_category_device": 0,
            "shopping_category_gender": 0,
            "shopping_category_age": 0,
            "shopping_keyword": 0,
            "shopping_keyword_device": 0,
            "shopping_keyword_gender": 0,
            "shopping_keyword_age": 0,
        }

    def datalab_search_trends(
        self,
        request: DataLabSearchTrendsRequest,
    ) -> Mapping[str, Any]:
        self.last_search_request = request
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

    def datalab_shopping_category_device_trends(
        self,
        request: DataLabShoppingCategoryDetailRequest,
    ) -> Mapping[str, Any]:
        self.calls["shopping_category_device"] += 1
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

    def datalab_shopping_category_gender_trends(
        self,
        request: DataLabShoppingCategoryDetailRequest,
    ) -> Mapping[str, Any]:
        self.calls["shopping_category_gender"] += 1
        return {
            "startDate": request.start_date,
            "endDate": request.end_date,
            "timeUnit": request.time_unit,
            "results": [
                {
                    "title": request.category,
                    "category": [request.category],
                    "data": [
                        {"period": "2026-03-01", "group": "f", "ratio": 61.4},
                        {"period": "2026-03-01", "group": "m", "ratio": 38.6},
                    ],
                }
            ],
        }

    def datalab_shopping_category_age_trends(
        self,
        request: DataLabShoppingCategoryDetailRequest,
    ) -> Mapping[str, Any]:
        self.calls["shopping_category_age"] += 1
        return {
            "startDate": request.start_date,
            "endDate": request.end_date,
            "timeUnit": request.time_unit,
            "results": [
                {
                    "title": request.category,
                    "category": [request.category],
                    "data": [
                        {"period": "2026-03-01", "group": "20", "ratio": 41.7},
                        {"period": "2026-03-01", "group": "30", "ratio": 58.3},
                    ],
                }
            ],
        }

    def datalab_shopping_keyword_trends(
        self,
        request: DataLabShoppingKeywordTrendsRequest,
    ) -> Mapping[str, Any]:
        self.calls["shopping_keyword"] += 1
        return {
            "startDate": request.start_date,
            "endDate": request.end_date,
            "timeUnit": request.time_unit,
            "results": [
                {
                    "title": request.keywords[0].name,
                    "category": [request.category],
                    "keyword": request.keywords[0].params,
                    "data": [{"period": "2026-03-01", "ratio": 44.8}],
                }
            ],
        }

    def datalab_shopping_keyword_device_trends(
        self,
        request: DataLabShoppingKeywordDetailRequest,
    ) -> Mapping[str, Any]:
        self.calls["shopping_keyword_device"] += 1
        return {
            "startDate": request.start_date,
            "endDate": request.end_date,
            "timeUnit": request.time_unit,
            "results": [
                {
                    "title": request.keyword,
                    "category": [request.category],
                    "keyword": [request.keyword],
                    "data": [
                        {"period": "2026-03-01", "group": "mo", "ratio": 73.0},
                        {"period": "2026-03-01", "group": "pc", "ratio": 27.0},
                    ],
                }
            ],
        }

    def datalab_shopping_keyword_gender_trends(
        self,
        request: DataLabShoppingKeywordDetailRequest,
    ) -> Mapping[str, Any]:
        self.calls["shopping_keyword_gender"] += 1
        return {
            "startDate": request.start_date,
            "endDate": request.end_date,
            "timeUnit": request.time_unit,
            "results": [
                {
                    "title": request.keyword,
                    "category": [request.category],
                    "keyword": [request.keyword],
                    "data": [
                        {"period": "2026-03-01", "group": "f", "ratio": 66.6},
                        {"period": "2026-03-01", "group": "m", "ratio": 33.4},
                    ],
                }
            ],
        }

    def datalab_shopping_keyword_age_trends(
        self,
        request: DataLabShoppingKeywordDetailRequest,
    ) -> Mapping[str, Any]:
        self.calls["shopping_keyword_age"] += 1
        return {
            "startDate": request.start_date,
            "endDate": request.end_date,
            "timeUnit": request.time_unit,
            "results": [
                {
                    "title": request.keyword,
                    "category": [request.category],
                    "keyword": [request.keyword],
                    "data": [
                        {"period": "2026-03-01", "group": "20", "ratio": 47.5},
                        {"period": "2026-03-01", "group": "30", "ratio": 52.5},
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

    def test_datalab_search_trends_accepts_api_hub_filters(self) -> None:
        self.tools.datalab_search_trends(
            start_date="2026-03-01",
            end_date="2026-03-18",
            time_unit="date",
            keyword_groups=[{"group_name": "파이썬", "keywords": ["파이썬"]}],
            device="pc",
            gender="f",
            ages=["3", "4"],
        )

        assert self.client.last_search_request is not None
        self.assertEqual(self.client.last_search_request.device, "pc")
        self.assertEqual(self.client.last_search_request.gender, "f")
        self.assertEqual(self.client.last_search_request.ages, ["3", "4"])

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

    def test_datalab_shopping_category_device_trends_returns_grouped_points(self) -> None:
        result = self.tools.datalab_shopping_category_device_trends(
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

    def test_datalab_shopping_category_gender_trends_returns_gender_groups(self) -> None:
        result = self.tools.datalab_shopping_category_gender_trends(
            start_date="2026-03-01",
            end_date="2026-03-18",
            time_unit="date",
            category="50000000",
            device="mo",
        )

        self.assertEqual(result["results"][0]["category"], ["50000000"])
        self.assertEqual(result["results"][0]["data"][0]["group"], "f")
        self.assertEqual(result["results"][0]["data"][1]["group"], "m")

    def test_datalab_shopping_category_age_trends_returns_age_groups(self) -> None:
        result = self.tools.datalab_shopping_category_age_trends(
            start_date="2026-03-01",
            end_date="2026-03-18",
            time_unit="date",
            category="50000000",
            gender="f",
        )

        self.assertEqual(result["results"][0]["data"][0]["group"], "20")
        self.assertEqual(result["results"][0]["data"][1]["group"], "30")

    def test_datalab_shopping_keyword_trends_returns_keywords(self) -> None:
        result = self.tools.datalab_shopping_keyword_trends(
            start_date="2026-03-01",
            end_date="2026-03-18",
            time_unit="week",
            category="50000000",
            keywords=[{"name": "러닝화", "params": ["러닝화"]}],
            device="pc",
        )

        self.assertEqual(result["results"][0]["title"], "러닝화")
        self.assertEqual(result["results"][0]["keywords"], ["러닝화"])
        self.assertEqual(result["results"][0]["category"], ["50000000"])

    def test_datalab_shopping_keyword_device_trends_returns_keyword_meta(self) -> None:
        result = self.tools.datalab_shopping_keyword_device_trends(
            start_date="2026-03-01",
            end_date="2026-03-18",
            time_unit="date",
            category="50000000",
            keyword="러닝화",
        )

        self.assertEqual(result["results"][0]["keywords"], ["러닝화"])
        self.assertEqual(result["results"][0]["data"][0]["group"], "mo")

    def test_datalab_shopping_keyword_gender_trends_returns_gender_groups(self) -> None:
        result = self.tools.datalab_shopping_keyword_gender_trends(
            start_date="2026-03-01",
            end_date="2026-03-18",
            time_unit="date",
            category="50000000",
            keyword="러닝화",
        )

        self.assertEqual(result["results"][0]["data"][0]["group"], "f")
        self.assertEqual(result["results"][0]["data"][1]["group"], "m")
        self.assertEqual(result["results"][0]["keywords"], ["러닝화"])

    def test_datalab_shopping_keyword_age_trends_returns_age_groups(self) -> None:
        result = self.tools.datalab_shopping_keyword_age_trends(
            start_date="2026-03-01",
            end_date="2026-03-18",
            time_unit="date",
            category="50000000",
            keyword="러닝화",
        )

        self.assertEqual(result["results"][0]["data"][0]["group"], "20")
        self.assertEqual(result["results"][0]["data"][1]["group"], "30")
        self.assertEqual(result["results"][0]["keywords"], ["러닝화"])

    def test_datalab_shopping_device_trends_keeps_backward_compatible_alias(self) -> None:
        result = self.tools.datalab_shopping_device_trends(
            start_date="2026-03-01",
            end_date="2026-03-18",
            time_unit="date",
            category="50000000",
        )

        self.assertEqual(result["results"][0]["title"], "50000000")
        self.assertEqual(self.client.calls["shopping_category_device"], 1)

    def test_datalab_search_trends_validates_keyword_groups(self) -> None:
        with self.assertRaises(ValidationError):
            self.tools.datalab_search_trends(
                start_date="2026-03-01",
                end_date="2026-03-18",
                time_unit="date",
                keyword_groups=[],
            )

    def test_search_trends_request_rejects_invalid_keyword_group_types(self) -> None:
        invalid_values = [
            "keyword",
            None,
            {"group_name": "파이썬", "keywords": ["파이썬"]},
            ["keyword"],
            [{"group_name": "파이썬", "keywords": ["파이썬"]}],
        ]

        for keyword_groups in invalid_values:
            with self.subTest(keyword_groups=keyword_groups):
                with self.assertRaises(ValidationError):
                    DataLabSearchTrendsRequest(
                        start_date="2026-03-01",
                        end_date="2026-03-18",
                        time_unit="date",
                        keyword_groups=keyword_groups,  # type: ignore[arg-type]
                    )

    def test_shopping_category_request_rejects_invalid_group_types(self) -> None:
        invalid_values = [
            "category",
            None,
            {"name": "패션의류", "params": ["50000000"]},
            ("category",),
            iter(["category"]),
            ["category"],
            [{"name": "패션의류", "params": ["50000000"]}],
        ]

        for categories in invalid_values:
            with self.subTest(categories=categories), self.assertRaises(
                ValidationError
            ):
                DataLabShoppingCategoryTrendsRequest(
                    start_date="2026-03-01",
                    end_date="2026-03-18",
                    time_unit="date",
                    categories=categories,  # type: ignore[arg-type]
                )

    def test_shopping_keyword_request_rejects_invalid_group_types(self) -> None:
        invalid_values = [
            "keyword",
            None,
            {"name": "러닝화", "params": ["러닝화"]},
            ("keyword",),
            iter(["keyword"]),
            ["keyword"],
            [{"name": "러닝화", "params": ["러닝화"]}],
        ]

        for keywords in invalid_values:
            with self.subTest(keywords=keywords), self.assertRaises(ValidationError):
                DataLabShoppingKeywordTrendsRequest(
                    start_date="2026-03-01",
                    end_date="2026-03-18",
                    time_unit="date",
                    category="50000000",
                    keywords=keywords,  # type: ignore[arg-type]
                )

    def test_datalab_search_trends_validates_api_hub_age_codes(self) -> None:
        with self.assertRaises(ValidationError):
            self.tools.datalab_search_trends(
                start_date="2026-03-01",
                end_date="2026-03-18",
                time_unit="date",
                keyword_groups=[{"group_name": "파이썬", "keywords": ["파이썬"]}],
                ages=["20"],
            )

    def test_datalab_search_trends_rejects_scalar_ages(self) -> None:
        with self.assertRaises(ValidationError):
            self.tools.datalab_search_trends(
                start_date="2026-03-01",
                end_date="2026-03-18",
                time_unit="date",
                keyword_groups=[{"group_name": "파이썬", "keywords": ["파이썬"]}],
                ages="34",  # type: ignore[arg-type]
            )

    def test_datalab_search_trends_rejects_scalar_keywords(self) -> None:
        with self.assertRaises(ValidationError):
            self.tools.datalab_search_trends(
                start_date="2026-03-01",
                end_date="2026-03-18",
                time_unit="date",
                keyword_groups=[{"group_name": "파이썬", "keywords": "파이썬"}],
            )

    def test_datalab_rejects_non_iterable_group_collections(self) -> None:
        invalid_calls = [
            lambda: self.tools.datalab_search_trends(
                start_date="2026-03-01",
                end_date="2026-03-18",
                time_unit="date",
                keyword_groups=None,  # type: ignore[arg-type]
            ),
            lambda: self.tools.datalab_shopping_category_trends(
                start_date="2026-03-01",
                end_date="2026-03-18",
                time_unit="date",
                categories=42,  # type: ignore[arg-type]
            ),
            lambda: self.tools.datalab_shopping_keyword_trends(
                start_date="2026-03-01",
                end_date="2026-03-18",
                time_unit="date",
                category="50000000",
                keywords=None,  # type: ignore[arg-type]
            ),
        ]

        for call in invalid_calls:
            with self.subTest(call=call), self.assertRaises(ValidationError):
                call()

    def test_datalab_canonical_group_field_is_not_overridden_by_alias(self) -> None:
        invalid_calls = [
            lambda: self.tools.datalab_search_trends(
                start_date="2026-03-01",
                end_date="2026-03-18",
                time_unit="date",
                keyword_groups=[
                    {
                        "group_name": "",
                        "groupName": "alias-name",
                        "keywords": ["파이썬"],
                    }
                ],
            ),
            lambda: self.tools.datalab_search_trends(
                start_date="2026-03-01",
                end_date="2026-03-18",
                time_unit="date",
                keyword_groups=[
                    {
                        "group_name": None,
                        "groupName": "alias-name",
                        "keywords": ["파이썬"],
                    }
                ],
            ),
            lambda: self.tools.datalab_shopping_category_trends(
                start_date="2026-03-01",
                end_date="2026-03-18",
                time_unit="date",
                categories=[
                    {
                        "name": "패션의류",
                        "params": None,
                        "param": ["50000000"],
                    }
                ],
            ),
        ]

        for call in invalid_calls:
            with self.subTest(call=call), self.assertRaises(ValidationError):
                call()

    def test_datalab_shopping_rejects_scalar_nested_params(self) -> None:
        invalid_calls = [
            lambda: self.tools.datalab_shopping_category_trends(
                start_date="2026-03-01",
                end_date="2026-03-18",
                time_unit="date",
                categories=[{"name": "패션의류", "params": "50000000"}],
            ),
            lambda: self.tools.datalab_shopping_keyword_trends(
                start_date="2026-03-01",
                end_date="2026-03-18",
                time_unit="date",
                category="50000000",
                keywords=[{"name": "러닝화", "params": "러닝화"}],
            ),
        ]

        for call in invalid_calls:
            with self.subTest(call=call), self.assertRaises(ValidationError):
                call()

    def test_datalab_rejects_reversed_date_range(self) -> None:
        with self.assertRaises(ValidationError):
            self.tools.datalab_search_trends(
                start_date="2026-03-19",
                end_date="2026-03-18",
                time_unit="date",
                keyword_groups=[{"group_name": "파이썬", "keywords": ["파이썬"]}],
            )

    def test_datalab_rejects_non_canonical_date_format(self) -> None:
        with self.assertRaises(ValidationError):
            self.tools.datalab_search_trends(
                start_date="2026-3-01",
                end_date="2026-10-01",
                time_unit="date",
                keyword_groups=[{"group_name": "파이썬", "keywords": ["파이썬"]}],
            )

    def test_datalab_search_trends_limits_keywords_per_group(self) -> None:
        with self.assertRaises(ValidationError):
            self.tools.datalab_search_trends(
                start_date="2026-03-01",
                end_date="2026-03-18",
                time_unit="date",
                keyword_groups=[
                    {
                        "group_name": "too-many",
                        "keywords": [f"keyword-{index}" for index in range(21)],
                    }
                ],
            )

    def test_datalab_search_trends_limits_keyword_groups(self) -> None:
        with self.assertRaises(ValidationError):
            self.tools.datalab_search_trends(
                start_date="2026-03-01",
                end_date="2026-03-18",
                time_unit="date",
                keyword_groups=[
                    {"group_name": f"group-{index}", "keywords": [f"keyword-{index}"]}
                    for index in range(6)
                ],
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

    def test_datalab_shopping_filters_reject_non_string_values(self) -> None:
        invalid_requests = [
            {"device": None},
            {"device": 1},
            {"gender": None},
            {"gender": 1},
        ]

        for invalid_filter in invalid_requests:
            with self.subTest(invalid_filter=invalid_filter), self.assertRaises(
                ValidationError
            ):
                DataLabShoppingCategoryDetailRequest(
                    start_date="2026-03-01",
                    end_date="2026-03-18",
                    time_unit="date",
                    category="50000000",
                    **invalid_filter,  # type: ignore[arg-type]
                )

    def test_datalab_shopping_keyword_trends_validates_keywords(self) -> None:
        with self.assertRaises(ValidationError):
            self.tools.datalab_shopping_keyword_trends(
                start_date="2026-03-01",
                end_date="2026-03-18",
                time_unit="date",
                category="50000000",
                keywords=[],
            )

    def test_datalab_shopping_keyword_device_trends_validates_keyword(self) -> None:
        with self.assertRaises(ValidationError):
            self.tools.datalab_shopping_keyword_device_trends(
                start_date="2026-03-01",
                end_date="2026-03-18",
                time_unit="date",
                category="50000000",
                keyword="   ",
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
