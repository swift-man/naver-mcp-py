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
)
from .models import (
    BlogSearchRequest,
    CafeArticleSearchRequest,
    DataLabShoppingCategoryTrendsRequest,
    DataLabShoppingDeviceTrendsRequest,
    DataLabSearchTrendsRequest,
    LocalSearchRequest,
    NewsSearchRequest,
    QueryOnlyRequest,
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
        self._max_retries = max(1, max_retries)

    def search_local(self, request: LocalSearchRequest) -> Mapping[str, Any]:
        return self._request_json("GET", "search/local.json", params=request.to_params())

    def search_blog(self, request: BlogSearchRequest) -> Mapping[str, Any]:
        return self._request_json("GET", "search/blog.json", params=request.to_params())

    def search_web(self, request: WebSearchRequest) -> Mapping[str, Any]:
        return self._request_json("GET", "search/webkr.json", params=request.to_params())

    def search_news(self, request: NewsSearchRequest) -> Mapping[str, Any]:
        return self._request_json("GET", "search/news.json", params=request.to_params())

    def search_cafearticle(
        self,
        request: CafeArticleSearchRequest,
    ) -> Mapping[str, Any]:
        return self._request_json(
            "GET",
            "search/cafearticle.json",
            params=request.to_params(),
        )

    def spell_check(self, request: QueryOnlyRequest) -> Mapping[str, Any]:
        return self._request_json("GET", "search/errata.json", params=request.to_params())

    def detect_adult_query(self, request: QueryOnlyRequest) -> Mapping[str, Any]:
        return self._request_json("GET", "search/adult.json", params=request.to_params())

    def datalab_search_trends(
        self,
        request: DataLabSearchTrendsRequest,
    ) -> Mapping[str, Any]:
        return self._request_json(
            "POST",
            "datalab/search",
            payload=request.to_payload(),
        )

    def datalab_shopping_category_trends(
        self,
        request: DataLabShoppingCategoryTrendsRequest,
    ) -> Mapping[str, Any]:
        return self._request_json(
            "POST",
            "datalab/shopping/categories",
            payload=request.to_payload(),
        )

    def datalab_shopping_device_trends(
        self,
        request: DataLabShoppingDeviceTrendsRequest,
    ) -> Mapping[str, Any]:
        return self._request_json(
            "POST",
            "datalab/shopping/category/device",
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
        url = self._build_url(endpoint, params=params)
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = self._build_headers()
        if payload is not None:
            headers["Content-Type"] = "application/json"

        for attempt in range(1, self._max_retries + 1):
            try:
                return self._transport(
                    method,
                    url,
                    headers,
                    body,
                    self.config.http_timeout_sec,
                )
            except NaverTimeoutError:
                if attempt >= self._max_retries:
                    raise
                self._sleep_fn(min(0.2 * attempt, 1.0))

        raise NaverAPIError("Naver API request failed")

    def _build_headers(self) -> dict[str, str]:
        self.config.require_credentials()
        return {
            "Accept": "application/json",
            "X-Naver-Client-Id": self.config.client_id,
            "X-Naver-Client-Secret": self.config.client_secret,
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
        request = urllib.request.Request(
            url=url,
            headers=dict(headers),
            data=body,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw_body = response.read().decode("utf-8")
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
        message = body.strip() or f"Naver API request failed with status {status_code}"
        if status_code in {401, 403}:
            raise NaverAuthError(message, status_code=status_code)
        if status_code == 429:
            raise NaverRateLimitError(message, status_code=status_code)
        if status_code == 408 or status_code >= 500:
            raise NaverTimeoutError(message, status_code=status_code)
        raise NaverAPIError(message, status_code=status_code)
