from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Mapping, Optional

from .config import NaverMCPConfig
from .errors import (
    NaverAPIError,
    NaverAuthError,
    NaverRateLimitError,
    NaverTimeoutError,
    raise_retired_search,
)
from .models import (
    BlogSearchRequest,
    BookAdvancedSearchRequest,
    BookSearchRequest,
    CafeArticleSearchRequest,
    DataLabSearchTrendsRequest,
    DataLabShoppingCategoryDetailRequest,
    DataLabShoppingCategoryTrendsRequest,
    DataLabShoppingKeywordDetailRequest,
    DataLabShoppingKeywordTrendsRequest,
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

Transport = Callable[
    [str, str, Mapping[str, str], Optional[bytes], float],
    Mapping[str, Any],
]


class NaverClient:
    def __init__(
        self,
        config: NaverMCPConfig,
        *,
        transport: Optional[Transport] = None,
        sleep_fn: Optional[Callable[[float], None]] = None,
        max_retries: int = 1,
    ) -> None:
        self.config = config
        self._transport = transport or self._default_transport
        self._sleep_fn = sleep_fn or time.sleep
        self._max_retries = max(0, max_retries)

    def search_local(self, request: LocalSearchRequest) -> Mapping[str, Any]:
        return self._request_json("GET", "search/v1/local", params=request.to_params())

    def search_blog(self, request: BlogSearchRequest) -> Mapping[str, Any]:
        return self._request_json("GET", "search/v1/blog", params=request.to_params())

    def search_web(self, request: WebSearchRequest) -> Mapping[str, Any]:
        return self._request_json("GET", "search/v1/webkr", params=request.to_params())

    def search_news(self, request: NewsSearchRequest) -> Mapping[str, Any]:
        return self._request_json("GET", "search/v1/news", params=request.to_params())

    def search_cafearticle(
        self,
        request: CafeArticleSearchRequest,
    ) -> Mapping[str, Any]:
        return self._request_json(
            "GET",
            "search/v1/cafearticle",
            params=request.to_params(),
        )

    def search_image(self, request: ImageSearchRequest) -> Mapping[str, Any]:
        return self._request_json("GET", "search/v1/image", params=request.to_params())

    def search_book(self, request: BookSearchRequest) -> Mapping[str, Any]:
        raise_retired_search("search_book")

    def search_book_advanced(
        self,
        request: BookAdvancedSearchRequest,
    ) -> Mapping[str, Any]:
        raise_retired_search("search_book_advanced")

    def search_encyc(self, request: EncycSearchRequest) -> Mapping[str, Any]:
        return self._request_json(
            "GET",
            "search/v1/encyc",
            params=request.to_params(),
        )

    def search_kin(self, request: KinSearchRequest) -> Mapping[str, Any]:
        return self._request_json("GET", "search/v1/kin", params=request.to_params())

    def search_shop(self, request: ShopSearchRequest) -> Mapping[str, Any]:
        raise_retired_search("search_shop")

    def search_doc(self, request: DocSearchRequest) -> Mapping[str, Any]:
        raise_retired_search("search_doc")

    def spell_check(self, request: QueryOnlyRequest) -> Mapping[str, Any]:
        return self._request_json("GET", "search/v1/errata", params=request.to_params())

    def detect_adult_query(self, request: QueryOnlyRequest) -> Mapping[str, Any]:
        return self._request_json("GET", "search/v1/adult", params=request.to_params())

    def datalab_search_trends(
        self,
        request: DataLabSearchTrendsRequest,
    ) -> Mapping[str, Any]:
        return self._request_json(
            "POST",
            "search-trend/v1/search",
            payload=request.to_payload(),
        )

    def datalab_shopping_category_trends(
        self,
        request: DataLabShoppingCategoryTrendsRequest,
    ) -> Mapping[str, Any]:
        return self._request_json(
            "POST",
            "shopping/v1/categories",
            payload=request.to_payload(),
        )

    def datalab_shopping_category_device_trends(
        self,
        request: DataLabShoppingCategoryDetailRequest,
    ) -> Mapping[str, Any]:
        return self._request_json(
            "POST",
            "shopping/v1/category/device",
            payload=request.to_payload(),
        )

    def datalab_shopping_category_gender_trends(
        self,
        request: DataLabShoppingCategoryDetailRequest,
    ) -> Mapping[str, Any]:
        return self._request_json(
            "POST",
            "shopping/v1/category/gender",
            payload=request.to_payload(),
        )

    def datalab_shopping_category_age_trends(
        self,
        request: DataLabShoppingCategoryDetailRequest,
    ) -> Mapping[str, Any]:
        return self._request_json(
            "POST",
            "shopping/v1/category/age",
            payload=request.to_payload(),
        )

    def datalab_shopping_keyword_trends(
        self,
        request: DataLabShoppingKeywordTrendsRequest,
    ) -> Mapping[str, Any]:
        return self._request_json(
            "POST",
            "shopping/v1/category/keywords",
            payload=request.to_payload(),
        )

    def datalab_shopping_keyword_device_trends(
        self,
        request: DataLabShoppingKeywordDetailRequest,
    ) -> Mapping[str, Any]:
        return self._request_json(
            "POST",
            "shopping/v1/category/keyword/device",
            payload=request.to_payload(),
        )

    def datalab_shopping_keyword_gender_trends(
        self,
        request: DataLabShoppingKeywordDetailRequest,
    ) -> Mapping[str, Any]:
        return self._request_json(
            "POST",
            "shopping/v1/category/keyword/gender",
            payload=request.to_payload(),
        )

    def datalab_shopping_keyword_age_trends(
        self,
        request: DataLabShoppingKeywordDetailRequest,
    ) -> Mapping[str, Any]:
        return self._request_json(
            "POST",
            "shopping/v1/category/keyword/age",
            payload=request.to_payload(),
        )

    def _request_json(
        self,
        method: str,
        endpoint: str,
        *,
        params: Optional[Mapping[str, object]] = None,
        payload: Optional[Mapping[str, object]] = None,
    ) -> Mapping[str, Any]:
        # 검색 계열과 DataLab 계열을 같은 공통 HTTP 진입점으로 묶어 둔다.
        url = self._build_url(endpoint, params=params)
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = self._build_headers()
        if payload is not None:
            headers["Content-Type"] = "application/json"

        # max_retries는 최초 요청 이후 허용할 추가 시도 횟수다.
        for attempt in range(self._max_retries + 1):
            try:
                response = self._transport(
                    method,
                    url,
                    headers,
                    body,
                    self.config.http_timeout_sec,
                )
                return self._validate_response_payload(endpoint, response)
            except NaverAPIError as exc:
                # 일시적 5xx만 재시도하고 timeout과 일일 한도 초과는 즉시 반환한다.
                if not exc.is_retryable or attempt >= self._max_retries:
                    raise
                self._sleep_fn(min(0.2 * (attempt + 1), 1.0))

    @staticmethod
    def _validate_response_payload(
        endpoint: str,
        payload: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        if not isinstance(payload, Mapping):
            raise NaverAPIError("Naver API returned an unexpected payload")

        if endpoint.startswith("search/v1/") and endpoint not in {
            "search/v1/errata",
            "search/v1/adult",
        }:
            items = payload.get("items", [])
            if not isinstance(items, list):
                raise NaverAPIError("Naver API returned invalid search items")
            for field_name in ("total", "start", "display"):
                value = payload.get(field_name)
                if value is None:
                    continue
                if isinstance(value, bool) or not isinstance(value, (int, str)):
                    raise NaverAPIError(
                        f"Naver API returned invalid search {field_name}"
                    )
                try:
                    int(value)
                except ValueError as exc:
                    raise NaverAPIError(
                        f"Naver API returned invalid search {field_name}"
                    ) from exc

        if endpoint.startswith(("search-trend/v1/", "shopping/v1/")):
            results = payload.get("results", [])
            if not isinstance(results, list):
                raise NaverAPIError("Naver API returned invalid DataLab results")
            for result in results:
                if not isinstance(result, Mapping):
                    continue
                data = result.get("data", [])
                if not isinstance(data, list):
                    raise NaverAPIError("Naver API returned invalid DataLab data")

        return payload

    def _build_headers(self) -> dict[str, str]:
        # 인증값이 없으면 여기서 즉시 실패시켜, 네트워크 호출 전에 문제를 드러낸다.
        self.config.require_credentials()
        return {
            "Accept": "application/json",
            "X-NCP-APIGW-API-KEY-ID": self.config.client_id,
            "X-NCP-APIGW-API-KEY": self.config.client_secret,
        }

    def _build_url(
        self,
        endpoint: str,
        *,
        params: Optional[Mapping[str, object]] = None,
    ) -> str:
        base = self.config.api_base_url.rstrip("/")
        url = f"{base}/{endpoint.lstrip('/')}"
        if not params:
            return url
        query_string = urllib.parse.urlencode(params)
        return f"{url}?{query_string}"

    def _default_transport(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: Optional[bytes],
        timeout: float,
    ) -> Mapping[str, Any]:
        # 표준 라이브러리만으로도 리눅스 서버 배포가 가능하도록 urllib 기반으로 구현한다.
        request = urllib.request.Request(
            url=url,
            headers=dict(headers),
            data=body,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw_body = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            raw_body = exc.read().decode("utf-8", errors="replace")
            self._raise_for_http_error(exc.code, raw_body)
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, socket.timeout) or "timed out" in str(exc.reason).lower():
                raise NaverTimeoutError("Naver API request timed out") from exc
            raise NaverAPIError("Naver API request failed", retryable=True) from exc
        except TimeoutError as exc:
            raise NaverTimeoutError("Naver API request timed out") from exc

        try:
            parsed = json.loads(raw_body or "{}")
        except json.JSONDecodeError as exc:
            raise NaverAPIError("Naver API returned invalid JSON") from exc
        if not isinstance(parsed, Mapping):
            raise NaverAPIError("Naver API returned an unexpected payload")
        return parsed

    def _raise_for_http_error(self, status_code: int, body: str) -> None:
        # 상위 계층이 안정적으로 처리할 수 있도록 HTTP 상태를 내부 에러 코드로 매핑한다.
        message = self._extract_error_message(body, status_code)
        if status_code in {401, 403}:
            raise NaverAuthError(message, status_code=status_code)
        if status_code == 429:
            raise NaverRateLimitError(message, status_code=status_code)
        if status_code == 408:
            raise NaverTimeoutError(message, status_code=status_code)
        if status_code >= 500:
            raise NaverAPIError(message, status_code=status_code, retryable=True)
        raise NaverAPIError(message, status_code=status_code)

    @staticmethod
    def _extract_error_message(body: str, status_code: int) -> str:
        fallback = body.strip() or f"Naver API request failed with status {status_code}"
        try:
            payload = json.loads(body)
        except (TypeError, json.JSONDecodeError):
            return fallback
        if not isinstance(payload, Mapping):
            return fallback

        gateway_error = payload.get("error")
        if isinstance(gateway_error, Mapping):
            message = gateway_error.get("message") or gateway_error.get("details")
            if message:
                return str(message)

        message = payload.get("errorMessage") or payload.get("errMsg")
        if message:
            return str(message)
        return fallback
