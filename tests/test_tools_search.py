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
    BookAdvancedSearchRequest,
    BookSearchRequest,
    CafeArticleSearchRequest,
    DocSearchRequest,
    EncycSearchRequest,
    ImageSearchRequest,
    KinSearchRequest,
    LocalSearchRequest,
    NewsSearchRequest,
    QueryOnlyRequest,
    ShopSearchRequest,
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

    def search_image(self, request: ImageSearchRequest) -> Mapping[str, Any]:
        self.calls.append(("image", request.query))
        return {
            "total": 1,
            "start": request.start,
            "display": request.display,
            "items": [
                {
                    "title": "<b>고양이</b> 사진",
                    "link": "https://example.com/image/full",
                    "thumbnail": "https://example.com/image/thumb.jpg",
                    "sizeheight": "480",
                    "sizewidth": "640",
                }
            ],
        }

    def search_book(self, request: BookSearchRequest) -> Mapping[str, Any]:
        self.calls.append(("book", request.query))
        return {
            "total": 1,
            "start": request.start,
            "display": request.display,
            "items": [
                {
                    "title": "<b>파이썬</b> 입문",
                    "link": "https://example.com/book",
                    "image": "https://example.com/book.jpg",
                    "author": "홍길동",
                    "discount": "18000",
                    "publisher": "테스트출판사",
                    "isbn": "1234567890",
                    "description": "기초부터 배우는 파이썬",
                    "pubdate": "20260318",
                }
            ],
        }

    def search_book_advanced(
        self,
        request: BookAdvancedSearchRequest,
    ) -> Mapping[str, Any]:
        self.calls.append(("book_advanced", request.query))
        return {
            "total": 1,
            "start": request.start,
            "display": request.display,
            "items": [
                {
                    "title": request.title or "고급 검색 책",
                    "link": "https://example.com/book/advanced",
                    "image": "https://example.com/book-advanced.jpg",
                    "author": "고급 저자",
                    "discount": "21000",
                    "publisher": "심화출판사",
                    "isbn": request.isbn or "9781234567890",
                    "description": "상세 검색 결과",
                    "pubdate": "20260317",
                }
            ],
        }

    def search_encyc(self, request: EncycSearchRequest) -> Mapping[str, Any]:
        self.calls.append(("encyc", request.query))
        return {
            "total": 1,
            "start": request.start,
            "display": request.display,
            "items": [
                {
                    "title": "<b>블랙홀</b>",
                    "link": "https://example.com/encyc",
                    "description": "중력이 매우 강한 천체",
                    "thumbnail": "https://example.com/encyc.jpg",
                }
            ],
        }

    def search_kin(self, request: KinSearchRequest) -> Mapping[str, Any]:
        self.calls.append(("kin", request.query))
        return {
            "total": 1,
            "start": request.start,
            "display": request.display,
            "items": [
                {
                    "title": "<b>파이썬</b> 설치 방법",
                    "link": "https://example.com/kin",
                    "description": "설치 질문 답변",
                }
            ],
        }

    def search_shop(self, request: ShopSearchRequest) -> Mapping[str, Any]:
        self.calls.append(("shop", request.query))
        return {
            "total": 1,
            "start": request.start,
            "display": request.display,
            "items": [
                {
                    "title": "<b>무선 이어폰</b>",
                    "link": "https://example.com/shop",
                    "image": "https://example.com/shop.jpg",
                    "lprice": "99000",
                    "hprice": "159000",
                    "mallName": "테스트몰",
                    "productId": "123456",
                    "productType": "2",
                    "brand": "테스트브랜드",
                    "maker": "테스트메이커",
                    "category1": "디지털/가전",
                    "category2": "음향가전",
                    "category3": "이어폰",
                    "category4": "",
                }
            ],
        }

    def search_doc(self, request: DocSearchRequest) -> Mapping[str, Any]:
        self.calls.append(("doc", request.query))
        return {
            "total": 1,
            "start": request.start,
            "display": request.display,
            "items": [
                {
                    "title": "<b>생성형 AI</b> 연구 보고서",
                    "link": "https://example.com/doc",
                    "description": "전문 자료 요약",
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

    def test_search_image_returns_image_fields(self) -> None:
        result = self.tools.search_image(query="고양이 사진", filter="large")

        self.assertEqual(result["source"], "image")
        self.assertEqual(result["items"][0]["thumbnail"], "https://example.com/image/thumb.jpg")
        self.assertEqual(result["items"][0]["size_height"], "480")
        self.assertEqual(result["items"][0]["size_width"], "640")

    def test_search_book_returns_book_fields(self) -> None:
        result = self.tools.search_book(query="파이썬 입문")

        self.assertEqual(result["source"], "book")
        self.assertEqual(result["items"][0]["author"], "홍길동")
        self.assertEqual(result["items"][0]["publisher"], "테스트출판사")
        self.assertEqual(result["items"][0]["isbn"], "1234567890")

    def test_search_book_advanced_accepts_title_only(self) -> None:
        result = self.tools.search_book_advanced(title="클린 코드")

        self.assertEqual(result["source"], "book")
        self.assertEqual(result["query"], "클린 코드")
        self.assertEqual(result["items"][0]["title"], "클린 코드")

    def test_search_encyc_returns_thumbnail(self) -> None:
        result = self.tools.search_encyc(query="블랙홀")

        self.assertEqual(result["source"], "encyc")
        self.assertEqual(result["items"][0]["thumbnail"], "https://example.com/encyc.jpg")

    def test_search_kin_supports_point_sort(self) -> None:
        result = self.tools.search_kin(query="파이썬 설치", sort="point")

        self.assertEqual(result["source"], "kin")
        self.assertEqual(result["items"][0]["title"], "파이썬 설치 방법")

    def test_search_shop_returns_price_and_mall_fields(self) -> None:
        result = self.tools.search_shop(query="무선 이어폰", exclude="used:cbshop")

        self.assertEqual(result["source"], "shop")
        self.assertEqual(result["items"][0]["low_price"], "99000")
        self.assertEqual(result["items"][0]["mall_name"], "테스트몰")
        self.assertEqual(result["items"][0]["brand"], "테스트브랜드")

    def test_search_doc_returns_generic_document_shape(self) -> None:
        result = self.tools.search_doc(query="생성형 AI")

        self.assertEqual(result["source"], "doc")
        self.assertEqual(result["items"][0]["title"], "생성형 AI 연구 보고서")

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

    def test_search_naver_auto_routes_book_queries(self) -> None:
        result = self.tools.search_naver_auto(query="파이썬 책", display=5)

        self.assertEqual(result["intent"], "book_search")
        self.assertEqual(result["sources"], ["book"])
        self.assertEqual(result["items"][0]["source"], "book")

    def test_search_naver_auto_deduplicates_community_results(self) -> None:
        result = self.tools.search_naver_auto(query="에어팟 사용기", display=5)

        self.assertEqual(result["intent"], "community_search")
        self.assertEqual(result["sources"], ["blog", "cafearticle"])
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["meta"]["deduplicated"], 1)

    def test_search_image_validates_filter(self) -> None:
        with self.assertRaises(ValidationError):
            self.tools.search_image(query="고양이", filter="huge")

    def test_search_shop_validates_exclude_options(self) -> None:
        with self.assertRaises(ValidationError):
            self.tools.search_shop(query="이어폰", exclude="used:invalid")

    def test_search_book_advanced_requires_title_or_isbn(self) -> None:
        with self.assertRaises(ValidationError):
            self.tools.search_book_advanced()

    def test_search_web_validates_empty_query(self) -> None:
        with self.assertRaises(ValidationError):
            self.tools.search_web(query="   ")


if __name__ == "__main__":
    unittest.main()
