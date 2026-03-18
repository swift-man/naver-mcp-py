from __future__ import annotations

import json
from typing import Any, Callable, Mapping, Optional, Protocol, Union

from .cache import TTLCache
from .config import NaverMCPConfig
from .models import (
    BlogSearchRequest,
    CafeArticleSearchRequest,
    LocalSearchRequest,
    NewsSearchRequest,
    QueryOnlyRequest,
    WebSearchRequest,
)
from .normalize import (
    normalize_adult_query_response,
    normalize_search_response,
    normalize_spell_check_response,
)

SearchRequest = Union[
    LocalSearchRequest,
    BlogSearchRequest,
    WebSearchRequest,
    NewsSearchRequest,
    CafeArticleSearchRequest,
]


class SearchClientProtocol(Protocol):
    def search_local(self, request: LocalSearchRequest) -> Mapping[str, Any]:
        ...

    def search_blog(self, request: BlogSearchRequest) -> Mapping[str, Any]:
        ...

    def search_web(self, request: WebSearchRequest) -> Mapping[str, Any]:
        ...

    def search_news(self, request: NewsSearchRequest) -> Mapping[str, Any]:
        ...

    def search_cafearticle(
        self,
        request: CafeArticleSearchRequest,
    ) -> Mapping[str, Any]:
        ...

    def spell_check(self, request: QueryOnlyRequest) -> Mapping[str, Any]:
        ...

    def detect_adult_query(self, request: QueryOnlyRequest) -> Mapping[str, Any]:
        ...


class SearchTools:
    AUXILIARY_CACHE_TTL_SEC = 1800
    # 자동 라우팅은 복잡한 NLP 대신, 설명 가능한 힌트 기반 규칙으로 유지한다.
    PLACE_HINTS = (
        "맛집",
        "식당",
        "음식점",
        "카페",
        "술집",
        "병원",
        "약국",
        "주차",
        "호텔",
        "숙소",
        "펜션",
        "미용실",
        "피부과",
        "역",
        "부동산",
    )
    NEWS_HINTS = ("뉴스", "속보", "기사", "보도", "발표", "브리핑", "단독")
    COMMUNITY_HINTS = (
        "후기",
        "리뷰",
        "추천",
        "사용기",
        "비교",
        "레시피",
        "만드는법",
        "팁",
        "꿀팁",
        "경험담",
    )

    def __init__(
        self,
        client: SearchClientProtocol,
        *,
        cache: Optional[TTLCache] = None,
        config: Optional[NaverMCPConfig] = None,
    ) -> None:
        self.client = client
        self.config = config or NaverMCPConfig()
        self.cache = cache or TTLCache(default_ttl_sec=self.config.cache_ttl_sec)

    def search_local(
        self,
        *,
        query: str,
        display: int = 5,
        start: int = 1,
        sort: str = "random",
    ) -> dict[str, Any]:
        request = LocalSearchRequest(query=query, display=display, start=start, sort=sort)
        return self._run_search("search_local", "local", request, self.client.search_local)

    def search_blog(
        self,
        *,
        query: str,
        display: int = 5,
        start: int = 1,
        sort: str = "sim",
    ) -> dict[str, Any]:
        request = BlogSearchRequest(query=query, display=display, start=start, sort=sort)
        return self._run_search("search_blog", "blog", request, self.client.search_blog)

    def search_web(
        self,
        *,
        query: str,
        display: int = 5,
        start: int = 1,
    ) -> dict[str, Any]:
        request = WebSearchRequest(query=query, display=display, start=start)
        return self._run_search("search_web", "web", request, self.client.search_web)

    def search_news(
        self,
        *,
        query: str,
        display: int = 5,
        start: int = 1,
        sort: str = "sim",
    ) -> dict[str, Any]:
        request = NewsSearchRequest(query=query, display=display, start=start, sort=sort)
        return self._run_search("search_news", "news", request, self.client.search_news)

    def search_cafearticle(
        self,
        *,
        query: str,
        display: int = 5,
        start: int = 1,
        sort: str = "sim",
    ) -> dict[str, Any]:
        request = CafeArticleSearchRequest(
            query=query,
            display=display,
            start=start,
            sort=sort,
        )
        return self._run_search(
            "search_cafearticle",
            "cafearticle",
            request,
            self.client.search_cafearticle,
        )

    def spell_check(self, *, query: str) -> dict[str, Any]:
        request = QueryOnlyRequest(query=query)
        return self._run_query_only_tool(
            "spell_check",
            request,
            self.client.spell_check,
            normalize_spell_check_response,
        )

    def detect_adult_query(self, *, query: str) -> dict[str, Any]:
        request = QueryOnlyRequest(query=query)
        return self._run_query_only_tool(
            "detect_adult_query",
            request,
            self.client.detect_adult_query,
            normalize_adult_query_response,
        )

    def search_naver_auto(
        self,
        *,
        query: str,
        display: int = 5,
    ) -> dict[str, Any]:
        # 편의 도구도 내부적으로는 검증 로직을 재사용하기 위해 WebSearchRequest 형태로 받는다.
        request = WebSearchRequest(query=query, display=display, start=1)
        cache_key = self._build_cache_key("search_naver_auto", request.to_params())
        cached = self.cache.get(cache_key)
        if cached is not None:
            cached["meta"]["cached"] = True
            return cached

        intent = self._detect_auto_intent(request.query)
        plans = self._build_auto_plan(intent, request.query, request.display)
        source_results = [plan["call"]() for plan in plans]
        unique_items = self._merge_auto_results(source_results)
        total_candidates = sum(len(result.get("items", [])) for result in source_results)

        normalized = {
            "query": request.query,
            "intent": intent,
            "sources": [str(plan["source"]) for plan in plans],
            "items": unique_items[: request.display],
            "meta": {
                "display": request.display,
                "returned": len(unique_items[: request.display]),
                "total_candidates": total_candidates,
                "deduplicated": max(total_candidates - len(unique_items), 0),
                "cached": False,
            },
        }
        self.cache.set(cache_key, normalized)
        return normalized

    def _run_search(
        self,
        tool_name: str,
        source: str,
        request: SearchRequest,
        client_method: Callable[[Any], Mapping[str, Any]],
    ) -> dict[str, Any]:
        cache_key = self._build_cache_key(tool_name, request.to_params())
        cached = self.cache.get(cache_key)
        if cached is not None:
            cached["meta"]["cached"] = True
            return cached

        payload = client_method(request)
        normalized = normalize_search_response(
            request.query,
            source,
            payload,
            display=request.display,
            start=request.start,
            cached=False,
        )
        self.cache.set(cache_key, normalized)
        return normalized

    def _run_query_only_tool(
        self,
        tool_name: str,
        request: QueryOnlyRequest,
        client_method: Callable[[QueryOnlyRequest], Mapping[str, Any]],
        normalizer: Callable[..., dict[str, Any]],
    ) -> dict[str, Any]:
        cache_key = self._build_cache_key(tool_name, request.to_params())
        cached = self.cache.get(cache_key)
        if cached is not None:
            cached["meta"]["cached"] = True
            return cached

        payload = client_method(request)
        normalized = normalizer(request.query, payload, cached=False)
        self.cache.set(cache_key, normalized, ttl_sec=self.AUXILIARY_CACHE_TTL_SEC)
        return normalized

    def _detect_auto_intent(self, query: str) -> str:
        # 어떤 규칙에 걸렸는지 추론 가능해야 하므로 단순한 우선순위 규칙으로 intent를 정한다.
        lowered = query.lower()
        if any(keyword in lowered for keyword in self.NEWS_HINTS):
            return "news_search"
        if "카페글" in lowered or "네이버카페" in lowered or "cafearticle" in lowered:
            return "community_search"
        if any(keyword in lowered for keyword in self.PLACE_HINTS):
            return "place_search"
        if any(keyword in lowered for keyword in self.COMMUNITY_HINTS):
            return "community_search"
        return "general_web"

    def _build_auto_plan(
        self,
        intent: str,
        query: str,
        display: int,
    ) -> list[dict[str, Any]]:
        # 검색 조합과 정렬 기준을 여기 한곳에 모아 두면 계약 문서와 코드 동기화가 쉽다.
        if intent == "place_search":
            return [
                {
                    "source": "local",
                    "call": lambda: self.search_local(
                        query=query,
                        display=display,
                        start=1,
                        sort="comment",
                    ),
                },
                {
                    "source": "blog",
                    "call": lambda: self.search_blog(
                        query=query,
                        display=display,
                        start=1,
                        sort="sim",
                    ),
                },
            ]
        if intent == "news_search":
            return [
                {
                    "source": "news",
                    "call": lambda: self.search_news(
                        query=query,
                        display=display,
                        start=1,
                        sort="date",
                    ),
                }
            ]
        if intent == "community_search":
            return [
                {
                    "source": "blog",
                    "call": lambda: self.search_blog(
                        query=query,
                        display=display,
                        start=1,
                        sort="sim",
                    ),
                },
                {
                    "source": "cafearticle",
                    "call": lambda: self.search_cafearticle(
                        query=query,
                        display=display,
                        start=1,
                        sort="sim",
                    ),
                },
            ]
        return [
            {
                "source": "web",
                "call": lambda: self.search_web(query=query, display=display, start=1),
            },
            {
                "source": "blog",
                "call": lambda: self.search_blog(
                    query=query,
                    display=display,
                    start=1,
                    sort="sim",
                ),
            },
        ]

    def _merge_auto_results(
        self,
        source_results: list[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        merged: list[dict[str, Any]] = []
        seen: set[str] = set()
        total_sources = max(len(source_results), 1)

        for source_index, result in enumerate(source_results):
            for item_index, item in enumerate(result.get("items", [])):
                if not isinstance(item, Mapping):
                    continue
                dedupe_key = self._build_item_dedupe_key(item)
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                normalized_item = dict(item)
                # source 우선순위가 높을수록 더 큰 score를 주어 병합 결과를 결정적으로 만든다.
                normalized_item["score"] = float((total_sources - source_index) * 1000 - item_index)
                merged.append(normalized_item)

        return merged

    @staticmethod
    def _build_item_dedupe_key(item: Mapping[str, Any]) -> str:
        originallink = str(item.get("originallink") or "").strip().lower()
        if originallink:
            # 외부 원문 링크가 있으면 가장 안정적인 중복 판별 기준으로 사용한다.
            return originallink

        link = str(item.get("link") or "").strip().lower()
        if link:
            return link

        title = str(item.get("title") or "").strip().lower()
        source = str(item.get("source") or "").strip().lower()
        return f"{source}:{title}"

    @staticmethod
    def _build_cache_key(tool_name: str, params: Mapping[str, object]) -> str:
        return json.dumps({"tool": tool_name, "params": params}, sort_keys=True)
