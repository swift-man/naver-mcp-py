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
    BlogSearchRequest,
    CafeArticleSearchRequest,
    LocalSearchRequest,
    NewsSearchRequest,
    QueryOnlyRequest,
    WebSearchRequest,
)
from naver_mcp.tools_search import SearchTools


class FakeSearchClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def search_local(self, request: LocalSearchRequest) -> Mapping[str, Any]:
        self.calls.append(("local", request.query))
        return {
            "total": 1,
            "start": request.start,
            "display": request.display,
            "items": [
                {
                    "title": "<b>판교역</b> 근처 식당",
                    "link": "https://example.com/local",
                    "description": "회식 장소",
                    "category": "한식",
                    "address": "성남시 분당구",
                    "roadAddress": "분당구 판교역로",
                    "telephone": "031-000-0000",
                    "mapx": "127",
                    "mapy": "37",
                }
            ],
        }

    def search_blog(self, request: BlogSearchRequest) -> Mapping[str, Any]:
        self.calls.append(("blog", request.query))
        if "사용기" in request.query:
            return {
                "total": 1,
                "start": request.start,
                "display": request.display,
                "items": [
                    {
                        "title": "<b>에어팟</b> 사용기",
                        "link": "https://example.com/blog/redirect",
                        "originallink": "https://shared.example.com/review",
                        "description": "실사용 후기",
                        "bloggername": "테스터",
                        "bloggerlink": "https://blog.example.com",
                        "postdate": "20260318",
                    }
                ],
            }
        return {
            "total": 1,
            "start": request.start,
            "display": request.display,
            "items": [
                {
                    "title": "<b>김치찌개</b> 레시피",
                    "link": "https://example.com/blog",
                    "originallink": "https://blog.example.com/post/1",
                    "description": "<b>집밥</b> 스타일",
                    "bloggername": "테스트 작성자",
                    "bloggerlink": "https://blog.example.com",
                    "postdate": "20260318",
                }
            ],
        }

    def search_web(self, request: WebSearchRequest) -> Mapping[str, Any]:
        self.calls.append(("web", request.query))
        return {
            "total": 1,
            "start": request.start,
            "display": request.display,
            "items": [
                {
                    "title": "<b>판교 카페</b> 모음",
                    "link": "https://example.com/web",
                    "description": "분위기 좋은 카페",
                }
            ],
        }

    def search_news(self, request: NewsSearchRequest) -> Mapping[str, Any]:
        self.calls.append(("news", request.query))
        return {
            "total": 1,
            "start": request.start,
            "display": request.display,
            "items": [
                {
                    "title": "<b>판교</b> 스타트업 투자",
                    "link": "https://example.com/news",
                    "originallink": "https://news.example.com/article/1",
                    "description": "투자 유치 기사",
                    "pubDate": "Wed, 18 Mar 2026 12:00:00 +0900",
                }
            ],
        }

    def search_cafearticle(
        self,
        request: CafeArticleSearchRequest,
    ) -> Mapping[str, Any]:
        self.calls.append(("cafearticle", request.query))
        if "사용기" in request.query:
            return {
                "total": 1,
                "start": request.start,
                "display": request.display,
                "items": [
                    {
                        "title": "에어팟 사용기",
                        "link": "https://shared.example.com/review",
                        "description": "중복 후기",
                        "cafename": "리뷰 카페",
                        "cafeurl": "https://cafe.example.com/review",
                    }
                ],
            }
        return {
            "total": 1,
            "start": request.start,
            "display": request.display,
            "items": [
                {
                    "title": "<b>판교 맛집</b> 모임 후기",
                    "link": "https://example.com/cafearticle",
                    "description": "모임 장소 추천",
                    "cafename": "판교 모임 카페",
                    "cafeurl": "https://cafe.example.com/pangyo",
                }
            ],
        }

    def spell_check(self, request: QueryOnlyRequest) -> Mapping[str, Any]:
        self.calls.append(("spell_check", request.query))
        return {"errata": "pangyo restaurants"}

    def detect_adult_query(self, request: QueryOnlyRequest) -> Mapping[str, Any]:
        self.calls.append(("detect_adult_query", request.query))
        return {"result": {"item": [{"adult": "1"}]}}


class SearchToolsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = FakeSearchClient()
        self.tools = SearchTools(self.client, cache=TTLCache(default_ttl_sec=60))

    def test_search_blog_returns_normalized_contract(self) -> None:
        result = self.tools.search_blog(query="김치찌개 레시피")

        self.assertEqual(result["query"], "김치찌개 레시피")
        self.assertEqual(result["source"], "blog")
        self.assertEqual(result["items"][0]["title"], "김치찌개 레시피")
        self.assertEqual(result["items"][0]["snippet"], "집밥 스타일")
        self.assertEqual(result["items"][0]["description"], "집밥 스타일")
        self.assertEqual(result["items"][0]["blogger_name"], "테스트 작성자")
        self.assertEqual(result["items"][0]["published_at"], "2026-03-18T00:00:00+09:00")
        self.assertFalse(result["meta"]["cached"])

    def test_search_news_normalizes_originallink_and_pubdate(self) -> None:
        result = self.tools.search_news(query="판교 스타트업 뉴스", sort="date")

        self.assertEqual(result["source"], "news")
        self.assertEqual(result["items"][0]["originallink"], "https://news.example.com/article/1")
        self.assertEqual(result["items"][0]["published_at"], "2026-03-18T12:00:00+09:00")

    def test_search_cafearticle_returns_cafe_fields(self) -> None:
        result = self.tools.search_cafearticle(query="판교 맛집 후기")

        self.assertEqual(result["source"], "cafearticle")
        self.assertEqual(result["items"][0]["cafe_name"], "판교 모임 카페")
        self.assertEqual(result["items"][0]["cafe_url"], "https://cafe.example.com/pangyo")

    def test_spell_check_uses_longer_cache_and_normalizes_output(self) -> None:
        first = self.tools.spell_check(query="pangyp restaurants")
        second = self.tools.spell_check(query="pangyp restaurants")

        self.assertEqual(first["corrected_query"], "pangyo restaurants")
        self.assertTrue(first["changed"])
        self.assertFalse(first["meta"]["cached"])
        self.assertTrue(second["meta"]["cached"])

    def test_detect_adult_query_parses_nested_payload(self) -> None:
        result = self.tools.detect_adult_query(query="adult query")

        self.assertTrue(result["is_adult"])
        self.assertFalse(result["meta"]["cached"])

    def test_search_local_uses_cache_on_repeat_calls(self) -> None:
        first = self.tools.search_local(query="판교 맛집", sort="comment")
        second = self.tools.search_local(query="판교 맛집", sort="comment")

        self.assertFalse(first["meta"]["cached"])
        self.assertTrue(second["meta"]["cached"])
        self.assertEqual(self.client.calls.count(("local", "판교 맛집")), 1)

    def test_search_naver_auto_routes_place_queries(self) -> None:
        result = self.tools.search_naver_auto(query="판교 맛집", display=5)

        self.assertEqual(result["intent"], "place_search")
        self.assertEqual(result["sources"], ["local", "blog"])
        self.assertEqual(result["items"][0]["source"], "local")
        self.assertFalse(result["meta"]["cached"])

    def test_search_naver_auto_deduplicates_community_results(self) -> None:
        result = self.tools.search_naver_auto(query="에어팟 사용기", display=5)

        self.assertEqual(result["intent"], "community_search")
        self.assertEqual(result["sources"], ["blog", "cafearticle"])
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["meta"]["deduplicated"], 1)

    def test_search_web_validates_empty_query(self) -> None:
        with self.assertRaises(ValidationError):
            self.tools.search_web(query="   ")


if __name__ == "__main__":
    unittest.main()
