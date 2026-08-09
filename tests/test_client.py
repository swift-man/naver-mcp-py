from __future__ import annotations

import http.client
import json
import sys
import unittest
import urllib.error
import urllib.parse
from pathlib import Path
from typing import Any, Mapping, Optional
from unittest import mock

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from naver_mcp.cache import MAX_CACHE_TTL_SEC
from naver_mcp.client import (
    DATALAB_GROUPED_ENDPOINTS,
    NaverClient,
    _SameOriginRedirectHandler,
)
from naver_mcp.config import NaverMCPConfig
from naver_mcp.errors import (
    NaverAPIError,
    NaverAuthError,
    NaverRateLimitError,
    NaverServiceUnavailableError,
    NaverTimeoutError,
    ValidationError,
)
from naver_mcp.models import (
    BlogSearchRequest,
    BookSearchRequest,
    CafeArticleSearchRequest,
    DataLabCategoryGroup,
    DataLabKeywordGroup,
    DataLabSearchTrendsRequest,
    DataLabShoppingCategoryDetailRequest,
    DataLabShoppingCategoryTrendsRequest,
    DataLabShoppingKeywordDetailRequest,
    DataLabShoppingKeywordGroup,
    DataLabShoppingKeywordTrendsRequest,
    EncycSearchRequest,
    ImageSearchRequest,
    KinSearchRequest,
    LocalSearchRequest,
    NewsSearchRequest,
    QueryOnlyRequest,
    WebSearchRequest,
)


def _datalab_response(results: Any) -> dict[str, Any]:
    return {
        "startDate": "2026-08-01",
        "endDate": "2026-08-08",
        "timeUnit": "date",
        "results": results,
    }


class RecordingTransport:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def __call__(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: Optional[bytes],
        timeout: float,
    ) -> Mapping[str, Any]:
        self.calls.append(
            {
                "method": method,
                "url": url,
                "headers": dict(headers),
                "body": body,
                "timeout": timeout,
            }
        )
        path = urllib.parse.urlsplit(url).path
        if path.startswith("/search/v1/") and path not in {
            "/search/v1/errata",
            "/search/v1/adult",
        }:
            return {"items": []}
        if path.startswith(("/search-trend/v1/", "/shopping/v1/")):
            request_payload = json.loads(body or b"{}")
            return {
                "startDate": request_payload["startDate"],
                "endDate": request_payload["endDate"],
                "timeUnit": request_payload["timeUnit"],
                "results": [],
            }
        if path == "/search/v1/errata":
            return {"errata": ""}
        if path == "/search/v1/adult":
            return {"adult": "0"}
        return {}


class NaverClientTest(unittest.TestCase):
    def setUp(self) -> None:
        self.transport = RecordingTransport()
        self.config = NaverMCPConfig(client_id="client-id", client_secret="client-secret")
        self.client = NaverClient(self.config, transport=self.transport)

    def test_config_prefers_api_hub_environment_variables(self) -> None:
        config = NaverMCPConfig.from_env(
            {
                "NAVER_API_HUB_CLIENT_ID": "hub-id",
                "NAVER_API_HUB_CLIENT_SECRET": "hub-secret",
                "NAVER_CLIENT_ID": "legacy-id",
                "NAVER_CLIENT_SECRET": "legacy-secret",
            }
        )

        self.assertEqual(config.client_id, "hub-id")
        self.assertEqual(config.client_secret, "hub-secret")
        self.assertEqual(config.api_base_url, "https://naverapihub.apigw.ntruss.com")

    def test_config_keeps_legacy_environment_variable_aliases(self) -> None:
        config = NaverMCPConfig.from_env(
            {
                "NAVER_CLIENT_ID": "legacy-id",
                "NAVER_CLIENT_SECRET": "legacy-secret",
            }
        )

        self.assertEqual(config.client_id, "legacy-id")
        self.assertEqual(config.client_secret, "legacy-secret")

    def test_config_does_not_mix_api_hub_and_legacy_credentials(self) -> None:
        cases = [
            {
                "NAVER_API_HUB_CLIENT_ID": "hub-id",
                "NAVER_CLIENT_SECRET": "legacy-secret",
            },
            {
                "NAVER_API_HUB_CLIENT_SECRET": "hub-secret",
                "NAVER_CLIENT_ID": "legacy-id",
            },
        ]

        for env in cases:
            with self.subTest(env=env):
                config = NaverMCPConfig.from_env(env)
                with self.assertRaises(ValidationError):
                    config.require_credentials()

    def test_config_accepts_api_base_url_override(self) -> None:
        config = NaverMCPConfig.from_env(
            {"NAVER_API_BASE_URL": "https://api.example.com/naver/"}
        )

        self.assertEqual(config.api_base_url, "https://api.example.com/naver/")

    def test_config_allows_http_api_base_url_only_for_loopback(self) -> None:
        for value in (
            "http://localhost:8080/naver",
            "http://127.0.0.1:8080/naver",
            "http://[::1]:8080/naver",
        ):
            with self.subTest(value=value):
                config = NaverMCPConfig(api_base_url=value)
                self.assertEqual(config.api_base_url, value)

    def test_config_rejects_unsafe_or_invalid_api_base_url(self) -> None:
        invalid_values = [
            "http://api.example.com",
            "ftp://api.example.com",
            "api.example.com",
            "https://",
            "https://user:password@api.example.com",
            "https://api.example.com?target=naver",
            "https://api.example.com:99999",
            None,
        ]

        for value in invalid_values:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                NaverMCPConfig(api_base_url=value)  # type: ignore[arg-type]

    def test_config_rejects_non_positive_or_non_finite_timeout(self) -> None:
        for value in ("0", "-1", "nan", "inf", "-inf"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                NaverMCPConfig.from_env({"NAVER_HTTP_TIMEOUT_SEC": value})

        for value in (True, 10**400):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                NaverMCPConfig(http_timeout_sec=value)

    def test_config_rejects_invalid_port(self) -> None:
        for value in (0, -1, 65536, True, 1.5):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                NaverMCPConfig(port=value)  # type: ignore[arg-type]

    def test_config_rejects_invalid_cache_ttl(self) -> None:
        for value in (-1, True, 1.5, MAX_CACHE_TTL_SEC + 1, 10**309):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                NaverMCPConfig(cache_ttl_sec=value)  # type: ignore[arg-type]

        self.assertEqual(NaverMCPConfig(cache_ttl_sec=0).cache_ttl_sec, 0)
        self.assertEqual(
            NaverMCPConfig(cache_ttl_sec=MAX_CACHE_TTL_SEC).cache_ttl_sec,
            MAX_CACHE_TTL_SEC,
        )

    def test_config_rejects_cache_ttl_above_limit_from_environment(self) -> None:
        with self.assertRaises(ValidationError):
            NaverMCPConfig.from_env({"NAVER_CACHE_TTL_SEC": str(10**309)})

    def test_config_validates_and_normalizes_transport(self) -> None:
        for value in ("stdio", "http", "sse", "streamable-http"):
            with self.subTest(value=value):
                self.assertEqual(NaverMCPConfig(transport=value).transport, value)

        self.assertEqual(NaverMCPConfig(transport=" STDIO ").transport, "stdio")
        for value in ("websocket", "", None):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                NaverMCPConfig(transport=value)  # type: ignore[arg-type]

    def test_search_requests_use_api_hub_paths_and_headers(self) -> None:
        self.client.search_local(LocalSearchRequest(query="카페"))
        self.client.search_blog(BlogSearchRequest(query="카페"))
        self.client.search_web(WebSearchRequest(query="카페"))
        self.client.search_news(NewsSearchRequest(query="카페"))
        self.client.search_cafearticle(CafeArticleSearchRequest(query="카페"))
        self.client.search_image(ImageSearchRequest(query="카페"))
        self.client.search_encyc(EncycSearchRequest(query="카페"))
        self.client.search_kin(KinSearchRequest(query="카페"))
        self.client.spell_check(QueryOnlyRequest(query="카페"))
        self.client.detect_adult_query(QueryOnlyRequest(query="카페"))

        paths = [urllib.parse.urlsplit(call["url"]).path for call in self.transport.calls]
        self.assertEqual(
            paths,
            [
                "/search/v1/local",
                "/search/v1/blog",
                "/search/v1/webkr",
                "/search/v1/news",
                "/search/v1/cafearticle",
                "/search/v1/image",
                "/search/v1/encyc",
                "/search/v1/kin",
                "/search/v1/errata",
                "/search/v1/adult",
            ],
        )
        headers = self.transport.calls[0]["headers"]
        self.assertEqual(headers["X-NCP-APIGW-API-KEY-ID"], "client-id")
        self.assertEqual(headers["X-NCP-APIGW-API-KEY"], "client-secret")
        self.assertNotIn("X-Naver-Client-Id", headers)

    def test_datalab_requests_use_api_hub_paths(self) -> None:
        search_request = DataLabSearchTrendsRequest(
            start_date="2026-08-01",
            end_date="2026-08-08",
            time_unit="date",
            keyword_groups=[DataLabKeywordGroup(group_name="파이썬", keywords=["파이썬"])],
        )
        category_request = DataLabShoppingCategoryTrendsRequest(
            start_date="2026-08-01",
            end_date="2026-08-08",
            time_unit="date",
            categories=[DataLabCategoryGroup(name="패션", params=["50000000"])],
        )
        category_detail_request = DataLabShoppingCategoryDetailRequest(
            start_date="2026-08-01",
            end_date="2026-08-08",
            time_unit="date",
            category="50000000",
        )
        keyword_request = DataLabShoppingKeywordTrendsRequest(
            start_date="2026-08-01",
            end_date="2026-08-08",
            time_unit="date",
            category="50000000",
            keywords=[DataLabShoppingKeywordGroup(name="정장", params=["정장"])],
        )
        keyword_detail_request = DataLabShoppingKeywordDetailRequest(
            start_date="2026-08-01",
            end_date="2026-08-08",
            time_unit="date",
            category="50000000",
            keyword="정장",
        )

        self.client.datalab_search_trends(search_request)
        self.client.datalab_shopping_category_trends(category_request)
        self.client.datalab_shopping_category_device_trends(category_detail_request)
        self.client.datalab_shopping_category_gender_trends(category_detail_request)
        self.client.datalab_shopping_category_age_trends(category_detail_request)
        self.client.datalab_shopping_keyword_trends(keyword_request)
        self.client.datalab_shopping_keyword_device_trends(keyword_detail_request)
        self.client.datalab_shopping_keyword_gender_trends(keyword_detail_request)
        self.client.datalab_shopping_keyword_age_trends(keyword_detail_request)

        paths = [urllib.parse.urlsplit(call["url"]).path for call in self.transport.calls]
        self.assertEqual(
            paths,
            [
                "/search-trend/v1/search",
                "/shopping/v1/categories",
                "/shopping/v1/category/device",
                "/shopping/v1/category/gender",
                "/shopping/v1/category/age",
                "/shopping/v1/category/keywords",
                "/shopping/v1/category/keyword/device",
                "/shopping/v1/category/keyword/gender",
                "/shopping/v1/category/keyword/age",
            ],
        )

    def test_optional_datalab_filters_are_omitted_when_empty(self) -> None:
        request = DataLabShoppingCategoryDetailRequest(
            start_date="2026-08-01",
            end_date="2026-08-08",
            time_unit="date",
            category="50000000",
        )

        self.client.datalab_shopping_category_device_trends(request)

        payload = json.loads(self.transport.calls[0]["body"].decode("utf-8"))
        self.assertNotIn("device", payload)
        self.assertNotIn("gender", payload)
        self.assertNotIn("ages", payload)

    def test_datalab_breakdown_requests_preserve_supported_filters(self) -> None:
        category_request = DataLabShoppingCategoryDetailRequest(
            start_date="2026-08-01",
            end_date="2026-08-08",
            time_unit="date",
            category="50000000",
            device="pc",
            gender="f",
            ages=["20", "30"],
        )
        keyword_request = DataLabShoppingKeywordDetailRequest(
            start_date="2026-08-01",
            end_date="2026-08-08",
            time_unit="date",
            category="50000000",
            keyword="정장",
            device="pc",
            gender="f",
            ages=["20", "30"],
        )
        calls = [
            (self.client.datalab_shopping_category_device_trends, category_request),
            (self.client.datalab_shopping_category_gender_trends, category_request),
            (self.client.datalab_shopping_category_age_trends, category_request),
            (self.client.datalab_shopping_keyword_device_trends, keyword_request),
            (self.client.datalab_shopping_keyword_gender_trends, keyword_request),
            (self.client.datalab_shopping_keyword_age_trends, keyword_request),
        ]

        for client_call, request in calls:
            with self.subTest(client_call=client_call.__name__):
                client_call(request)
                payload = json.loads(self.transport.calls[-1]["body"].decode("utf-8"))
                self.assertEqual(payload["device"], "pc")
                self.assertEqual(payload["gender"], "f")
                self.assertEqual(payload["ages"], ["20", "30"])

    def test_search_trend_filters_are_sent_when_configured(self) -> None:
        request = DataLabSearchTrendsRequest(
            start_date="2026-08-01",
            end_date="2026-08-08",
            time_unit="date",
            keyword_groups=[DataLabKeywordGroup(group_name="파이썬", keywords=["파이썬"])],
            device="pc",
            gender="f",
            ages=["3", "4"],
        )

        self.client.datalab_search_trends(request)

        payload = json.loads(self.transport.calls[0]["body"].decode("utf-8"))
        self.assertEqual(payload["device"], "pc")
        self.assertEqual(payload["gender"], "f")
        self.assertEqual(payload["ages"], ["3", "4"])

    def test_retired_search_does_not_make_network_request(self) -> None:
        with self.assertRaises(NaverServiceUnavailableError):
            self.client.search_book(BookSearchRequest(query="파이썬"))

        self.assertEqual(self.transport.calls, [])

    def test_api_hub_gateway_error_message_is_extracted(self) -> None:
        with self.assertRaises(NaverAuthError) as context:
            self.client._raise_for_http_error(
                401,
                '{"error":{"errorCode":"200","message":"Authentication Failed"}}',
            )

        self.assertEqual(context.exception.message, "Authentication Failed")

    def test_api_hub_error_message_variants_are_extracted(self) -> None:
        cases = [
            ('{"error":{"details":"gateway details"}}', "gateway details"),
            ('{"errorMessage":"search error"}', "search error"),
            ("plain text error", "plain text error"),
            ("", "Naver API request failed with status 400"),
        ]

        for body, expected in cases:
            with self.subTest(body=body):
                self.assertEqual(self.client._extract_error_message(body, 400), expected)

    def test_server_error_is_retryable_api_error_not_timeout(self) -> None:
        with self.assertRaises(NaverAPIError) as context:
            self.client._raise_for_http_error(500, '{"errMsg":"temporary server error"}')

        self.assertEqual(context.exception.message, "temporary server error")
        self.assertTrue(context.exception.is_retryable)

    def test_retryable_api_error_is_retried(self) -> None:
        calls = 0
        sleeps: list[float] = []

        def transport(
            method: str,
            url: str,
            headers: Mapping[str, str],
            body: Optional[bytes],
            timeout: float,
        ) -> Mapping[str, Any]:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise NaverAPIError("temporary server error", retryable=True)
            return {"items": []}

        client = NaverClient(
            self.config,
            transport=transport,
            sleep_fn=sleeps.append,
            max_retries=2,
        )

        client.search_blog(BlogSearchRequest(query="네이버"))

        self.assertEqual(calls, 2)
        self.assertEqual(sleeps, [0.2])

    def test_default_retry_count_retries_once(self) -> None:
        calls = 0
        sleeps: list[float] = []

        def transport(
            method: str,
            url: str,
            headers: Mapping[str, str],
            body: Optional[bytes],
            timeout: float,
        ) -> Mapping[str, Any]:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise NaverAPIError("temporary server error", retryable=True)
            return {"items": []}

        client = NaverClient(
            self.config,
            transport=transport,
            sleep_fn=sleeps.append,
        )

        client.search_blog(BlogSearchRequest(query="네이버"))

        self.assertEqual(calls, 2)
        self.assertEqual(sleeps, [0.2])

    def test_malformed_success_payload_is_rejected(self) -> None:
        payloads = [
            {},
            {"items": None},
            {"items": [None]},
            {"items": ["not-an-object"]},
            {"items": [], "total": "not-a-number"},
        ]

        for payload in payloads:
            with self.subTest(payload=payload):
                client = NaverClient(
                    self.config,
                    transport=lambda *args, payload=payload: payload,
                )
                with self.assertRaises(NaverAPIError):
                    client.search_blog(BlogSearchRequest(query="네이버"))

    def test_malformed_adult_query_response_is_rejected(self) -> None:
        payloads = [
            {},
            {"adult": None},
            {"adult": 0},
            {"adult": "2"},
            {"adult": "unknown"},
        ]

        for payload in payloads:
            with self.subTest(payload=payload):
                client = NaverClient(
                    self.config,
                    transport=lambda *args, payload=payload: payload,
                )
                with self.assertRaises(NaverAPIError):
                    client.detect_adult_query(QueryOnlyRequest(query="검색어"))

    def test_adult_query_response_accepts_documented_codes(self) -> None:
        responses = [
            {"adult": "0"},
            {"result": {"adult": "1"}},
            {"result": {"item": [{"adult": "1"}]}},
            {"item": {"adult": "0"}},
            {"items": [{"adult": "1"}]},
        ]

        for response in responses:
            with self.subTest(response=response):
                client = NaverClient(
                    self.config,
                    transport=lambda *args, response=response: response,
                )

                payload = client.detect_adult_query(QueryOnlyRequest(query="검색어"))

                self.assertEqual(payload, response)

    def test_malformed_errata_response_is_rejected(self) -> None:
        payloads = [
            {},
            {"errata": None},
            {"errata": 0},
            {"result": {"errata": None}},
        ]

        for payload in payloads:
            with self.subTest(payload=payload):
                client = NaverClient(
                    self.config,
                    transport=lambda *args, payload=payload: payload,
                )
                with self.assertRaises(NaverAPIError):
                    client.spell_check(QueryOnlyRequest(query="검색어"))

    def test_errata_response_accepts_string_including_empty_value(self) -> None:
        responses = [
            {"errata": ""},
            {"errata": "네이버"},
            {"result": {"errata": "네이버"}},
        ]

        for response in responses:
            with self.subTest(response=response):
                client = NaverClient(
                    self.config,
                    transport=lambda *args, response=response: response,
                )

                payload = client.spell_check(QueryOnlyRequest(query="spdlqj"))

                self.assertEqual(payload, response)

    def test_malformed_datalab_success_payload_is_rejected(self) -> None:
        request = DataLabSearchTrendsRequest(
            start_date="2026-08-01",
            end_date="2026-08-08",
            time_unit="date",
            keyword_groups=[DataLabKeywordGroup(group_name="파이썬", keywords=["파이썬"])],
        )

        def search_trend_payload(data: Any) -> dict[str, Any]:
            return _datalab_response(
                [
                    {
                        "title": "파이썬",
                        "keywords": ["파이썬"],
                        "data": data,
                    }
                ]
            )

        payloads = [
            {},
            _datalab_response([None]),
            _datalab_response([{}]),
            search_trend_payload(None),
            search_trend_payload([None]),
            search_trend_payload([{"ratio": 1}]),
            search_trend_payload([{"period": None, "ratio": 1}]),
            search_trend_payload([{"period": 20260801, "ratio": 1}]),
            search_trend_payload([{"period": "   ", "ratio": 1}]),
            search_trend_payload([{"period": "2026-08-01", "ratio": None}]),
            search_trend_payload([{"period": "2026-08-01", "ratio": True}]),
            search_trend_payload([{"period": "2026-08-01", "ratio": "12.3"}]),
            search_trend_payload(
                [{"period": "2026-08-01", "ratio": float("nan")}]
            ),
            search_trend_payload(
                [{"period": "2026-08-01", "ratio": float("inf")}]
            ),
            search_trend_payload([{"period": "2026-08-01", "ratio": 10**400}]),
            search_trend_payload([{"period": "2026-08-01", "ratio": -1}]),
            search_trend_payload([{"period": "2026-08-01", "ratio": 100.1}]),
            search_trend_payload([{"period": "2026-8-1", "ratio": 50}]),
            search_trend_payload([{"period": "2026-02-30", "ratio": 50}]),
        ]

        for payload in payloads:
            with self.subTest(payload=payload):
                client = NaverClient(
                    self.config,
                    transport=lambda *args, payload=payload: payload,
                )
                with self.assertRaises(NaverAPIError):
                    client.datalab_search_trends(request)

    def test_datalab_ratio_accepts_documented_boundaries(self) -> None:
        request = DataLabSearchTrendsRequest(
            start_date="2026-08-01",
            end_date="2026-08-08",
            time_unit="date",
            keyword_groups=[DataLabKeywordGroup(group_name="파이썬", keywords=["파이썬"])],
        )

        for ratio in (0, 100):
            response = _datalab_response(
                [
                    {
                        "title": "파이썬",
                        "keywords": ["파이썬"],
                        "data": [{"period": "2026-08-01", "ratio": ratio}],
                    }
                ]
            )
            with self.subTest(ratio=ratio):
                client = NaverClient(
                    self.config,
                    transport=lambda *args, response=response: response,
                )

                payload = client.datalab_search_trends(request)

                self.assertEqual(payload, response)

    def test_grouped_datalab_endpoints_require_string_group(self) -> None:
        endpoints = [
            "shopping/v1/category/device",
            "shopping/v1/category/gender",
            "shopping/v1/category/age",
            "shopping/v1/category/keyword/device",
            "shopping/v1/category/keyword/gender",
            "shopping/v1/category/keyword/age",
        ]
        invalid_groups = [None, 10, {}, "   "]

        for endpoint in endpoints:
            metadata = {"title": "테스트"}
            if endpoint in {
                "shopping/v1/category/keyword/device",
                "shopping/v1/category/keyword/gender",
                "shopping/v1/category/keyword/age",
            }:
                metadata["keyword"] = ["정장"]
            else:
                metadata["category"] = ["50000000"]
            for group in invalid_groups:
                payload = _datalab_response(
                    [
                        {
                            **metadata,
                            "data": [
                                {
                                    "period": "2026-08-01",
                                    "group": group,
                                    "ratio": 50,
                                }
                            ]
                        }
                    ]
                )
                with (
                    self.subTest(endpoint=endpoint, group=group),
                    self.assertRaises(NaverAPIError),
                ):
                    NaverClient._validate_response_payload(endpoint, payload)

            missing_group = _datalab_response(
                [
                    {
                        **metadata,
                        "data": [{"period": "2026-08-01", "ratio": 50}],
                    }
                ]
            )
            with self.subTest(endpoint=endpoint), self.assertRaises(NaverAPIError):
                NaverClient._validate_response_payload(endpoint, missing_group)

    def test_aggregate_datalab_endpoints_do_not_require_group(self) -> None:
        for endpoint in (
            "search-trend/v1/search",
            "shopping/v1/categories",
            "shopping/v1/category/keywords",
        ):
            result = {
                "title": "테스트",
                "data": [{"period": "2026-08-01", "ratio": 50}],
            }
            if endpoint == "search-trend/v1/search":
                result["keywords"] = ["파이썬"]
            elif endpoint == "shopping/v1/categories":
                result["category"] = ["50000000"]
            else:
                result["keyword"] = ["정장"]
            payload = _datalab_response([result])
            with self.subTest(endpoint=endpoint):
                self.assertEqual(
                    NaverClient._validate_response_payload(endpoint, payload),
                    payload,
                )

    def test_datalab_keyword_endpoints_require_string_array_metadata(self) -> None:
        endpoints = [
            "shopping/v1/category/keywords",
            "shopping/v1/category/keyword/device",
            "shopping/v1/category/keyword/gender",
            "shopping/v1/category/keyword/age",
        ]
        invalid_keywords = [None, "정장", [], [None], [10], ["   "], {}]

        for endpoint in endpoints:
            for keywords in invalid_keywords:
                point = {"period": "2026-08-01", "ratio": 50}
                if endpoint != "shopping/v1/category/keywords":
                    point["group"] = "mo"
                payload = _datalab_response(
                    [
                        {
                            "title": "정장",
                            "keyword": keywords,
                            "data": [point],
                        }
                    ]
                )
                with (
                    self.subTest(endpoint=endpoint, keywords=keywords),
                    self.assertRaises(NaverAPIError),
                ):
                    NaverClient._validate_response_payload(endpoint, payload)

    def test_datalab_keyword_endpoints_accept_string_array_metadata(self) -> None:
        for endpoint in (
            "shopping/v1/category/keywords",
            "shopping/v1/category/keyword/device",
            "shopping/v1/category/keyword/gender",
            "shopping/v1/category/keyword/age",
        ):
            point = {"period": "2026-08-01", "ratio": 50}
            if endpoint.endswith("/device"):
                point["group"] = "mo"
            elif endpoint.endswith("/gender"):
                point["group"] = "f"
            elif endpoint.endswith("/age"):
                point["group"] = "20"
            payload = _datalab_response(
                [
                    {
                        "title": "정장",
                        "keyword": ["정장"],
                        "data": [point],
                    }
                ]
            )
            with self.subTest(endpoint=endpoint):
                self.assertEqual(
                    NaverClient._validate_response_payload(endpoint, payload),
                    payload,
                )

    def test_datalab_result_titles_require_non_empty_strings(self) -> None:
        endpoints = [
            "search-trend/v1/search",
            "shopping/v1/categories",
            "shopping/v1/category/device",
            "shopping/v1/category/gender",
            "shopping/v1/category/age",
            "shopping/v1/category/keywords",
            "shopping/v1/category/keyword/device",
            "shopping/v1/category/keyword/gender",
            "shopping/v1/category/keyword/age",
        ]

        for endpoint in endpoints:
            for title in (None, 10, {}, "   "):
                payload = _datalab_response([{"title": title, "data": []}])
                with (
                    self.subTest(endpoint=endpoint, title=title),
                    self.assertRaises(NaverAPIError),
                ):
                    NaverClient._validate_response_payload(endpoint, payload)

    def test_search_and_category_metadata_require_string_arrays(self) -> None:
        endpoints = {
            "search-trend/v1/search": "keywords",
            "shopping/v1/categories": "category",
            "shopping/v1/category/device": "category",
            "shopping/v1/category/gender": "category",
            "shopping/v1/category/age": "category",
        }
        invalid_values = [None, "값", [], [None], [10], ["   "], {}]

        for endpoint, field_name in endpoints.items():
            for value in invalid_values:
                point = {"period": "2026-08-01", "ratio": 50}
                if endpoint in DATALAB_GROUPED_ENDPOINTS:
                    point["group"] = "mo"
                payload = _datalab_response(
                    [
                        {
                            "title": "테스트",
                            field_name: value,
                            "data": [point],
                        }
                    ]
                )
                with (
                    self.subTest(endpoint=endpoint, value=value),
                    self.assertRaises(NaverAPIError),
                ):
                    NaverClient._validate_response_payload(endpoint, payload)

    def test_optional_datalab_array_metadata_is_validated_when_present(self) -> None:
        payload = _datalab_response(
            [
                {
                    "title": "정장",
                    "keyword": ["정장"],
                    "category": {"unexpected": "50000000"},
                    "data": [{"period": "2026-08-01", "ratio": 50}],
                }
            ]
        )

        with self.assertRaises(NaverAPIError):
            NaverClient._validate_response_payload(
                "shopping/v1/category/keywords",
                payload,
            )

    def test_datalab_top_level_metadata_is_validated(self) -> None:
        valid = _datalab_response([])
        invalid_payloads = []
        for field_name in ("startDate", "endDate", "timeUnit"):
            missing = dict(valid)
            missing.pop(field_name)
            invalid_payloads.append(missing)
        invalid_payloads.extend(
            [
                {**valid, "startDate": None},
                {**valid, "startDate": {}},
                {**valid, "startDate": "2026-8-1"},
                {**valid, "startDate": "2026-02-30"},
                {**valid, "startDate": "2026-08-09"},
                {**valid, "endDate": 20260808},
                {**valid, "endDate": "2026-08-8"},
                {**valid, "timeUnit": {}},
                {**valid, "timeUnit": "year"},
            ]
        )

        for payload in invalid_payloads:
            with self.subTest(payload=payload), self.assertRaises(NaverAPIError):
                NaverClient._validate_response_payload(
                    "search-trend/v1/search",
                    payload,
                )

        self.assertEqual(
            NaverClient._validate_response_payload(
                "search-trend/v1/search",
                valid,
            ),
            valid,
        )

    def test_grouped_datalab_endpoints_validate_documented_group_values(self) -> None:
        endpoints = {
            "shopping/v1/category/device": ("pc", "tablet"),
            "shopping/v1/category/gender": ("m", "unknown"),
            "shopping/v1/category/age": ("20", "70"),
            "shopping/v1/category/keyword/device": ("mo", "tablet"),
            "shopping/v1/category/keyword/gender": ("f", "unknown"),
            "shopping/v1/category/keyword/age": ("60", "70"),
        }

        for endpoint, (valid_group, invalid_group) in endpoints.items():
            metadata = {"title": "테스트"}
            if "/keyword/" in endpoint:
                metadata["keyword"] = ["정장"]
            else:
                metadata["category"] = ["50000000"]

            def response(group: str) -> dict[str, Any]:
                return _datalab_response(
                    [
                        {
                            **metadata,
                            "data": [
                                {
                                    "period": "2026-08-01",
                                    "group": group,
                                    "ratio": 50,
                                }
                            ],
                        }
                    ]
                )

            valid_payload = response(valid_group)
            with self.subTest(endpoint=endpoint, group=valid_group):
                self.assertEqual(
                    NaverClient._validate_response_payload(endpoint, valid_payload),
                    valid_payload,
                )
            with (
                self.subTest(endpoint=endpoint, group=invalid_group),
                self.assertRaises(NaverAPIError),
            ):
                NaverClient._validate_response_payload(
                    endpoint,
                    response(invalid_group),
                )

    def test_aggregate_datalab_endpoints_reject_unexpected_group(self) -> None:
        payload = _datalab_response(
            [
                {
                    "title": "파이썬",
                    "keywords": ["파이썬"],
                    "data": [
                        {
                            "period": "2026-08-01",
                            "group": "pc",
                            "ratio": 50,
                        }
                    ],
                }
            ]
        )

        with self.assertRaises(NaverAPIError):
            NaverClient._validate_response_payload(
                "search-trend/v1/search",
                payload,
            )

    def test_default_transport_replaces_invalid_utf8_bytes(self) -> None:
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = b'{"note":"\xff"}'

        with mock.patch("naver_mcp.client._safe_urlopen", return_value=response):
            payload = self.client._default_transport(
                "GET",
                "https://api.example.com/test",
                {},
                None,
                1.0,
            )

        self.assertEqual(payload["note"], "\ufffd")

    def test_interrupted_http_responses_are_retryable_api_errors(self) -> None:
        errors = [
            http.client.IncompleteRead(b'{"items":', 1),
            http.client.RemoteDisconnected("remote closed connection"),
        ]

        for error in errors:
            with self.subTest(error=error):
                response = mock.MagicMock()
                response.__enter__.return_value = response
                response.read.side_effect = error

                with mock.patch(
                    "naver_mcp.client._safe_urlopen",
                    return_value=response,
                ):
                    with self.assertRaises(NaverAPIError) as context:
                        self.client._default_transport(
                            "GET",
                            "https://api.example.com/test",
                            {},
                            None,
                            1.0,
                        )

                self.assertTrue(context.exception.is_retryable)

    def test_interrupted_http_error_bodies_are_structured(self) -> None:
        cases = [
            (
                http.client.IncompleteRead(b'{"error":', 1),
                NaverAPIError,
                True,
            ),
            (
                http.client.RemoteDisconnected("remote closed connection"),
                NaverAPIError,
                True,
            ),
            (TimeoutError("timed out"), NaverTimeoutError, True),
        ]

        for read_error, expected_error, retryable in cases:
            with self.subTest(read_error=read_error):
                error_body = mock.MagicMock()
                error_body.read.side_effect = read_error
                http_error = urllib.error.HTTPError(
                    "https://api.example.com/test",
                    500,
                    "Server Error",
                    {},
                    error_body,
                )

                with mock.patch(
                    "naver_mcp.client._safe_urlopen",
                    side_effect=http_error,
                ):
                    with self.assertRaises(expected_error) as context:
                        self.client._default_transport(
                            "GET",
                            "https://api.example.com/test",
                            {},
                            None,
                            1.0,
                        )

                self.assertEqual(context.exception.is_retryable, retryable)

    def test_interrupted_error_body_preserves_non_retryable_http_status(self) -> None:
        cases = [
            (401, NaverAuthError, False),
            (403, NaverAuthError, False),
            (429, NaverRateLimitError, False),
        ]

        for status_code, expected_error, retryable in cases:
            with self.subTest(status_code=status_code):
                error_body = mock.MagicMock()
                error_body.read.side_effect = http.client.IncompleteRead(b"", 1)
                http_error = urllib.error.HTTPError(
                    "https://api.example.com/test",
                    status_code,
                    "Request Error",
                    {},
                    error_body,
                )

                with mock.patch(
                    "naver_mcp.client._safe_urlopen",
                    side_effect=http_error,
                ):
                    with self.assertRaises(expected_error) as context:
                        self.client._default_transport(
                            "GET",
                            "https://api.example.com/test",
                            {},
                            None,
                            1.0,
                        )

                self.assertEqual(context.exception.status_code, status_code)
                self.assertEqual(context.exception.is_retryable, retryable)

    def test_redirect_handler_allows_only_same_origin(self) -> None:
        handler = _SameOriginRedirectHandler()
        request = urllib.request.Request(
            "https://api.example.com/search",
            headers={"X-NCP-APIGW-API-KEY": "secret"},
        )

        redirected = handler.redirect_request(
            request,
            None,
            302,
            "Found",
            {},
            "https://api.example.com:443/next",
        )

        self.assertIsNotNone(redirected)
        assert redirected is not None
        self.assertEqual(
            redirected.get_header("X-ncp-apigw-api-key"),
            "secret",
        )

        unsafe_urls = [
            "https://other.example.com/next",
            "http://api.example.com/next",
            "https://api.example.com:444/next",
            "https://api.example.com:99999/next",
            "https://user@api.example.com/next",
            "ftp://api.example.com/next",
        ]
        for unsafe_url in unsafe_urls:
            with self.subTest(unsafe_url=unsafe_url), self.assertRaises(NaverAPIError):
                handler.redirect_request(
                    request,
                    None,
                    302,
                    "Found",
                    {},
                    unsafe_url,
                )

    def test_timeout_fails_fast_without_retry(self) -> None:
        calls = 0
        sleeps: list[float] = []

        def transport(
            method: str,
            url: str,
            headers: Mapping[str, str],
            body: Optional[bytes],
            timeout: float,
        ) -> Mapping[str, Any]:
            nonlocal calls
            calls += 1
            raise NaverTimeoutError("Naver API request timed out")

        client = NaverClient(
            self.config,
            transport=transport,
            sleep_fn=sleeps.append,
        )

        with self.assertRaises(NaverTimeoutError):
            client.search_blog(BlogSearchRequest(query="네이버"))

        self.assertEqual(calls, 1)
        self.assertEqual(sleeps, [])

    def test_non_retryable_auth_error_is_not_retried(self) -> None:
        calls = 0
        sleeps: list[float] = []

        def transport(
            method: str,
            url: str,
            headers: Mapping[str, str],
            body: Optional[bytes],
            timeout: float,
        ) -> Mapping[str, Any]:
            nonlocal calls
            calls += 1
            raise NaverAuthError("Authentication Failed")

        client = NaverClient(
            self.config,
            transport=transport,
            sleep_fn=sleeps.append,
            max_retries=3,
        )

        with self.assertRaises(NaverAuthError):
            client.search_blog(BlogSearchRequest(query="네이버"))

        self.assertEqual(calls, 1)
        self.assertEqual(sleeps, [])

    def test_rate_limit_error_is_not_retried(self) -> None:
        calls = 0
        sleeps: list[float] = []

        def transport(
            method: str,
            url: str,
            headers: Mapping[str, str],
            body: Optional[bytes],
            timeout: float,
        ) -> Mapping[str, Any]:
            nonlocal calls
            calls += 1
            raise NaverRateLimitError("Daily quota exceeded")

        client = NaverClient(
            self.config,
            transport=transport,
            sleep_fn=sleeps.append,
            max_retries=3,
        )

        with self.assertRaises(NaverRateLimitError):
            client.search_blog(BlogSearchRequest(query="네이버"))

        self.assertEqual(calls, 1)
        self.assertEqual(sleeps, [])
        error = NaverRateLimitError("Daily quota exceeded")
        self.assertFalse(error.is_retryable)
        self.assertFalse(error.to_dict()["error"]["retryable"])


if __name__ == "__main__":
    unittest.main()
