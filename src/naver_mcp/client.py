from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
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

    def search_image(self, request: ImageSearchRequest) -> Mapping[str, Any]:
        return self._request_json("GET", "search/image.json", params=request.to_params())

    def search_book(self, request: BookSearchRequest) -> Mapping[str, Any]:
        return self._request_json("GET", "search/book.json", params=request.to_params())

    def search_book_advanced(
        self,
        request: BookAdvancedSearchRequest,
    ) -> Mapping[str, Any]:
        return self._request_xml_rss("GET", "search/book_adv.xml", params=request.to_params())

    def search_encyc(self, request: EncycSearchRequest) -> Mapping[str, Any]:
        return self._request_json(
            "GET",
            "search/encyc.json",
            params=request.to_params(),
        )

    def search_kin(self, request: KinSearchRequest) -> Mapping[str, Any]:
        return self._request_json("GET", "search/kin.json", params=request.to_params())

    def search_shop(self, request: ShopSearchRequest) -> Mapping[str, Any]:
        return self._request_json("GET", "search/shop.json", params=request.to_params())

    def search_doc(self, request: DocSearchRequest) -> Mapping[str, Any]:
        return self._request_json("GET", "search/doc.json", params=request.to_params())

    def spell_check(self, request: QueryOnlyRequest) -> Mapping[str, Any]:
        return self._request_json("GET", "search/errata.json", params=request.to_params())

    def detect_adult_query(self, request: QueryOnlyRequest) -> Mapping[str, Any]:
        return self._request_json("GET", "search/adult.json", params=request.to_params())

    def datalab_search_trends(
        self,
        request: DataLabSearchTrendsRequest,
    ) -> Mapping[str, Any]:
        return self._request_json("POST", "datalab/search", payload=request.to_payload())

    def datalab_shopping_category_trends(
        self,
        request: DataLabShoppingCategoryTrendsRequest,
    ) -> Mapping[str, Any]:
        return self._request_json(
            "POST",
            "datalab/shopping/categories",
            payload=request.to_payload(),
        )

    def datalab_shopping_category_device_trends(
        self,
        request: DataLabShoppingCategoryDetailRequest,
    ) -> Mapping[str, Any]:
        return self._request_json(
            "POST",
            "datalab/shopping/category/device",
            payload=request.to_payload(),
        )

    def datalab_shopping_category_gender_trends(
        self,
        request: DataLabShoppingCategoryDetailRequest,
    ) -> Mapping[str, Any]:
        return self._request_json(
            "POST",
            "datalab/shopping/category/gender",
            payload=request.to_payload(),
        )

    def datalab_shopping_category_age_trends(
        self,
        request: DataLabShoppingCategoryDetailRequest,
    ) -> Mapping[str, Any]:
        return self._request_json(
            "POST",
            "datalab/shopping/category/age",
            payload=request.to_payload(),
        )

    def datalab_shopping_keyword_trends(
        self,
        request: DataLabShoppingKeywordTrendsRequest,
    ) -> Mapping[str, Any]:
        return self._request_json(
            "POST",
            "datalab/shopping/category/keywords",
            payload=request.to_payload(),
        )

    def datalab_shopping_keyword_device_trends(
        self,
        request: DataLabShoppingKeywordDetailRequest,
    ) -> Mapping[str, Any]:
        return self._request_json(
            "POST",
            "datalab/shopping/category/keyword/device",
            payload=request.to_payload(),
        )

    def datalab_shopping_keyword_gender_trends(
        self,
        request: DataLabShoppingKeywordDetailRequest,
    ) -> Mapping[str, Any]:
        return self._request_json(
            "POST",
            "datalab/shopping/category/keyword/gender",
            payload=request.to_payload(),
        )

    def datalab_shopping_keyword_age_trends(
        self,
        request: DataLabShoppingKeywordDetailRequest,
    ) -> Mapping[str, Any]:
        return self._request_json(
            "POST",
            "datalab/shopping/category/keyword/age",
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
                # timeout만 짧게 재시도하고, 그 외 에러는 바로 상위로 올린다.
                if attempt >= self._max_retries:
                    raise
                self._sleep_fn(min(0.2 * attempt, 1.0))

        raise NaverAPIError("Naver API request failed")

    def _request_xml_rss(
        self,
        method: str,
        endpoint: str,
        *,
        params: Optional[Mapping[str, object]] = None,
    ) -> Mapping[str, Any]:
        # book_adv는 XML만 제공하므로 RSS 형태를 공통 dict로 변환해 상위 계층에 맞춘다.
        url = self._build_url(endpoint, params=params)
        headers = self._build_headers()
        raw_body = self._request_raw(method, url, headers, None)
        return self._parse_rss_xml(raw_body)

    def _build_headers(self) -> dict[str, str]:
        # 인증값이 없으면 여기서 즉시 실패시켜, 네트워크 호출 전에 문제를 드러낸다.
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

    def _request_raw(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: Optional[bytes],
    ) -> str:
        request = urllib.request.Request(
            url=url,
            headers=dict(headers),
            data=body,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.http_timeout_sec) as response:
                return response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raw_body = exc.read().decode("utf-8", errors="replace")
            self._raise_for_http_error(exc.code, raw_body)
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, socket.timeout) or "timed out" in str(exc.reason).lower():
                raise NaverTimeoutError("Naver API request timed out") from exc
            raise NaverAPIError("Naver API request failed", retryable=True) from exc
        except TimeoutError as exc:
            raise NaverTimeoutError("Naver API request timed out") from exc

        raise NaverAPIError("Naver API request failed")

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

    def _parse_rss_xml(self, raw_body: str) -> Mapping[str, Any]:
        try:
            root = ET.fromstring(raw_body)
        except ET.ParseError as exc:
            raise NaverAPIError("Naver API returned invalid XML") from exc

        channel = root.find("channel")
        if channel is None:
            raise NaverAPIError("Naver API returned an unexpected XML payload")

        items: list[dict[str, str]] = []
        for item_element in channel.findall("item"):
            item: dict[str, str] = {}
            for child in list(item_element):
                item[child.tag] = child.text or ""
            items.append(item)

        return {
            "total": self._safe_int(channel.findtext("total"), len(items)),
            "start": self._safe_int(channel.findtext("start"), 1),
            "display": self._safe_int(channel.findtext("display"), len(items)),
            "items": items,
        }

    @staticmethod
    def _safe_int(value: Optional[str], default: int) -> int:
        try:
            return int(value or default)
        except (TypeError, ValueError):
            return default

    def _raise_for_http_error(self, status_code: int, body: str) -> None:
        # 상위 계층이 안정적으로 처리할 수 있도록 HTTP 상태를 내부 에러 코드로 매핑한다.
        message = body.strip() or f"Naver API request failed with status {status_code}"
        if status_code in {401, 403}:
            raise NaverAuthError(message, status_code=status_code)
        if status_code == 429:
            raise NaverRateLimitError(message, status_code=status_code)
        if status_code == 408 or status_code >= 500:
            raise NaverTimeoutError(message, status_code=status_code)
        raise NaverAPIError(message, status_code=status_code)
