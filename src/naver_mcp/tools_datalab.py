from __future__ import annotations

import json
from typing import Any, Callable, Mapping, Optional, Protocol

from .cache import TTLCache
from .config import NaverMCPConfig
from .models import (
    DataLabCategoryGroup,
    DataLabSearchTrendsRequest,
    DataLabKeywordGroup,
    DataLabShoppingCategoryDetailRequest,
    DataLabShoppingCategoryTrendsRequest,
    DataLabShoppingKeywordDetailRequest,
    DataLabShoppingKeywordGroup,
    DataLabShoppingKeywordTrendsRequest,
)
from .normalize import (
    normalize_datalab_category_trends_response,
    normalize_datalab_device_trends_response,
    normalize_datalab_search_trends_response_with_meta,
)


class DataLabClientProtocol(Protocol):
    def datalab_search_trends(
        self,
        request: DataLabSearchTrendsRequest,
    ) -> Mapping[str, Any]:
        ...

    def datalab_shopping_category_trends(
        self,
        request: DataLabShoppingCategoryTrendsRequest,
    ) -> Mapping[str, Any]:
        ...

    def datalab_shopping_category_device_trends(
        self,
        request: DataLabShoppingCategoryDetailRequest,
    ) -> Mapping[str, Any]:
        ...

    def datalab_shopping_category_gender_trends(
        self,
        request: DataLabShoppingCategoryDetailRequest,
    ) -> Mapping[str, Any]:
        ...

    def datalab_shopping_category_age_trends(
        self,
        request: DataLabShoppingCategoryDetailRequest,
    ) -> Mapping[str, Any]:
        ...

    def datalab_shopping_keyword_trends(
        self,
        request: DataLabShoppingKeywordTrendsRequest,
    ) -> Mapping[str, Any]:
        ...

    def datalab_shopping_keyword_device_trends(
        self,
        request: DataLabShoppingKeywordDetailRequest,
    ) -> Mapping[str, Any]:
        ...

    def datalab_shopping_keyword_gender_trends(
        self,
        request: DataLabShoppingKeywordDetailRequest,
    ) -> Mapping[str, Any]:
        ...

    def datalab_shopping_keyword_age_trends(
        self,
        request: DataLabShoppingKeywordDetailRequest,
    ) -> Mapping[str, Any]:
        ...


class DataLabTools:
    def __init__(
        self,
        client: DataLabClientProtocol,
        *,
        cache: Optional[TTLCache] = None,
        config: Optional[NaverMCPConfig] = None,
    ) -> None:
        self.client = client
        self.config = config or NaverMCPConfig()
        self.cache = cache or TTLCache(default_ttl_sec=max(self.config.cache_ttl_sec, 1800))

    def datalab_search_trends(
        self,
        *,
        start_date: str,
        end_date: str,
        time_unit: str,
        keyword_groups: list[dict[str, Any]],
    ) -> dict[str, Any]:
        # 외부 입력은 dict로 받고, 내부에서는 검증 가능한 요청 모델로 즉시 변환한다.
        groups = [
            DataLabKeywordGroup(
                group_name=str(group.get("group_name") or group.get("groupName") or ""),
                keywords=list(group.get("keywords") or []),
            )
            for group in keyword_groups
        ]
        request = DataLabSearchTrendsRequest(
            start_date=start_date,
            end_date=end_date,
            time_unit=time_unit,
            keyword_groups=groups,
        )
        return self._run_datalab_tool(
            "datalab_search_trends",
            request.to_payload(),
            lambda: self.client.datalab_search_trends(request),
            normalize_datalab_search_trends_response_with_meta,
        )

    def datalab_shopping_category_trends(
        self,
        *,
        start_date: str,
        end_date: str,
        time_unit: str,
        categories: list[dict[str, Any]],
        device: str = "",
        gender: str = "",
        ages: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        request = self._build_category_trends_request(
            start_date=start_date,
            end_date=end_date,
            time_unit=time_unit,
            categories=categories,
            device=device,
            gender=gender,
            ages=ages,
        )
        return self._run_datalab_tool(
            "datalab_shopping_category_trends",
            request.to_payload(),
            lambda: self.client.datalab_shopping_category_trends(request),
            normalize_datalab_category_trends_response,
        )

    def datalab_shopping_category_device_trends(
        self,
        *,
        start_date: str,
        end_date: str,
        time_unit: str,
        category: str,
        device: str = "",
        gender: str = "",
        ages: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        request = self._build_category_detail_request(
            start_date=start_date,
            end_date=end_date,
            time_unit=time_unit,
            category=category,
            device=device,
            gender=gender,
            ages=ages,
        )
        return self._run_datalab_tool(
            "datalab_shopping_category_device_trends",
            request.to_payload(),
            lambda: self.client.datalab_shopping_category_device_trends(request),
            normalize_datalab_device_trends_response,
        )

    def datalab_shopping_category_gender_trends(
        self,
        *,
        start_date: str,
        end_date: str,
        time_unit: str,
        category: str,
        device: str = "",
        gender: str = "",
        ages: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        request = self._build_category_detail_request(
            start_date=start_date,
            end_date=end_date,
            time_unit=time_unit,
            category=category,
            device=device,
            gender=gender,
            ages=ages,
        )
        return self._run_datalab_tool(
            "datalab_shopping_category_gender_trends",
            request.to_payload(),
            lambda: self.client.datalab_shopping_category_gender_trends(request),
            normalize_datalab_device_trends_response,
        )

    def datalab_shopping_category_age_trends(
        self,
        *,
        start_date: str,
        end_date: str,
        time_unit: str,
        category: str,
        device: str = "",
        gender: str = "",
        ages: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        request = self._build_category_detail_request(
            start_date=start_date,
            end_date=end_date,
            time_unit=time_unit,
            category=category,
            device=device,
            gender=gender,
            ages=ages,
        )
        return self._run_datalab_tool(
            "datalab_shopping_category_age_trends",
            request.to_payload(),
            lambda: self.client.datalab_shopping_category_age_trends(request),
            normalize_datalab_device_trends_response,
        )

    def datalab_shopping_keyword_trends(
        self,
        *,
        start_date: str,
        end_date: str,
        time_unit: str,
        category: str,
        keywords: list[dict[str, Any]],
        device: str = "",
        gender: str = "",
        ages: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        request = self._build_keyword_trends_request(
            start_date=start_date,
            end_date=end_date,
            time_unit=time_unit,
            category=category,
            keywords=keywords,
            device=device,
            gender=gender,
            ages=ages,
        )
        return self._run_datalab_tool(
            "datalab_shopping_keyword_trends",
            request.to_payload(),
            lambda: self.client.datalab_shopping_keyword_trends(request),
            normalize_datalab_category_trends_response,
        )

    def datalab_shopping_keyword_device_trends(
        self,
        *,
        start_date: str,
        end_date: str,
        time_unit: str,
        category: str,
        keyword: str,
        device: str = "",
        gender: str = "",
        ages: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        request = self._build_keyword_detail_request(
            start_date=start_date,
            end_date=end_date,
            time_unit=time_unit,
            category=category,
            keyword=keyword,
            device=device,
            gender=gender,
            ages=ages,
        )
        return self._run_datalab_tool(
            "datalab_shopping_keyword_device_trends",
            request.to_payload(),
            lambda: self.client.datalab_shopping_keyword_device_trends(request),
            normalize_datalab_device_trends_response,
        )

    def datalab_shopping_keyword_gender_trends(
        self,
        *,
        start_date: str,
        end_date: str,
        time_unit: str,
        category: str,
        keyword: str,
        device: str = "",
        gender: str = "",
        ages: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        request = self._build_keyword_detail_request(
            start_date=start_date,
            end_date=end_date,
            time_unit=time_unit,
            category=category,
            keyword=keyword,
            device=device,
            gender=gender,
            ages=ages,
        )
        return self._run_datalab_tool(
            "datalab_shopping_keyword_gender_trends",
            request.to_payload(),
            lambda: self.client.datalab_shopping_keyword_gender_trends(request),
            normalize_datalab_device_trends_response,
        )

    def datalab_shopping_keyword_age_trends(
        self,
        *,
        start_date: str,
        end_date: str,
        time_unit: str,
        category: str,
        keyword: str,
        device: str = "",
        gender: str = "",
        ages: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        request = self._build_keyword_detail_request(
            start_date=start_date,
            end_date=end_date,
            time_unit=time_unit,
            category=category,
            keyword=keyword,
            device=device,
            gender=gender,
            ages=ages,
        )
        return self._run_datalab_tool(
            "datalab_shopping_keyword_age_trends",
            request.to_payload(),
            lambda: self.client.datalab_shopping_keyword_age_trends(request),
            normalize_datalab_device_trends_response,
        )

    # 기존 이름과의 호환성을 위해 category/device 엔드포인트의 별칭으로 유지한다.
    def datalab_shopping_device_trends(
        self,
        *,
        start_date: str,
        end_date: str,
        time_unit: str,
        category: str,
        device: str = "",
        gender: str = "",
        ages: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        return self.datalab_shopping_category_device_trends(
            start_date=start_date,
            end_date=end_date,
            time_unit=time_unit,
            category=category,
            device=device,
            gender=gender,
            ages=ages,
        )

    def _build_category_trends_request(
        self,
        *,
        start_date: str,
        end_date: str,
        time_unit: str,
        categories: list[dict[str, Any]],
        device: str,
        gender: str,
        ages: Optional[list[str]],
    ) -> DataLabShoppingCategoryTrendsRequest:
        category_groups = [
            DataLabCategoryGroup(
                name=str(group.get("name") or ""),
                params=list(group.get("params") or group.get("param") or []),
            )
            for group in categories
        ]
        return DataLabShoppingCategoryTrendsRequest(
            start_date=start_date,
            end_date=end_date,
            time_unit=time_unit,
            categories=category_groups,
            device=device,
            gender=gender,
            ages=list(ages or []),
        )

    def _build_category_detail_request(
        self,
        *,
        start_date: str,
        end_date: str,
        time_unit: str,
        category: str,
        device: str,
        gender: str,
        ages: Optional[list[str]],
    ) -> DataLabShoppingCategoryDetailRequest:
        return DataLabShoppingCategoryDetailRequest(
            start_date=start_date,
            end_date=end_date,
            time_unit=time_unit,
            category=category,
            device=device,
            gender=gender,
            ages=list(ages or []),
        )

    def _build_keyword_trends_request(
        self,
        *,
        start_date: str,
        end_date: str,
        time_unit: str,
        category: str,
        keywords: list[dict[str, Any]],
        device: str,
        gender: str,
        ages: Optional[list[str]],
    ) -> DataLabShoppingKeywordTrendsRequest:
        # category/param 이름 차이를 여기서 흡수해 MCP 입력 형태를 단순하게 유지한다.
        keyword_groups = [
            DataLabShoppingKeywordGroup(
                name=str(group.get("name") or ""),
                params=list(group.get("params") or group.get("param") or []),
            )
            for group in keywords
        ]
        return DataLabShoppingKeywordTrendsRequest(
            start_date=start_date,
            end_date=end_date,
            time_unit=time_unit,
            category=category,
            keywords=keyword_groups,
            device=device,
            gender=gender,
            ages=list(ages or []),
        )

    def _build_keyword_detail_request(
        self,
        *,
        start_date: str,
        end_date: str,
        time_unit: str,
        category: str,
        keyword: str,
        device: str,
        gender: str,
        ages: Optional[list[str]],
    ) -> DataLabShoppingKeywordDetailRequest:
        return DataLabShoppingKeywordDetailRequest(
            start_date=start_date,
            end_date=end_date,
            time_unit=time_unit,
            category=category,
            keyword=keyword,
            device=device,
            gender=gender,
            ages=list(ages or []),
        )

    def _run_datalab_tool(
        self,
        tool_name: str,
        payload: Mapping[str, object],
        client_call: Callable[[], Mapping[str, Any]],
        normalizer: Callable[..., dict[str, Any]],
    ) -> dict[str, Any]:
        # DataLab은 비교적 갱신 주기가 길어 캐시 효율이 높으므로 공통 진입점에서 캐시를 관리한다.
        cache_key = self._build_cache_key(tool_name, payload)
        cached = self.cache.get(cache_key)
        if cached is not None:
            cached["meta"]["cached"] = True
            return cached

        response_payload = client_call()
        normalized = normalizer(response_payload, cached=False)
        self.cache.set(cache_key, normalized)
        return normalized

    @staticmethod
    def _build_cache_key(tool_name: str, payload: Mapping[str, object]) -> str:
        return json.dumps({"tool": tool_name, "payload": payload}, sort_keys=True)
