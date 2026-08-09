from __future__ import annotations

import json
import sys
import unittest
import urllib.parse
from pathlib import Path
from typing import Any, Mapping, Optional
from unittest import mock

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from naver_mcp.client import NaverClient
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

    def test_config_rejects_non_positive_or_non_finite_timeout(self) -> None:
        for value in ("0", "-1", "nan", "inf", "-inf"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                NaverMCPConfig.from_env({"NAVER_HTTP_TIMEOUT_SEC": value})

        for value in (True, 10**400):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                NaverMCPConfig(http_timeout_sec=value)

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
            return {}

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
            return {}

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
            {"items": None},
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

    def test_malformed_datalab_success_payload_is_rejected(self) -> None:
        request = DataLabSearchTrendsRequest(
            start_date="2026-08-01",
            end_date="2026-08-08",
            time_unit="date",
            keyword_groups=[DataLabKeywordGroup(group_name="파이썬", keywords=["파이썬"])],
        )
        payloads = [
            {"results": [None]},
            {"results": [{"data": None}]},
            {"results": [{"data": [None]}]},
            {"results": [{"data": [{"ratio": None}]}]},
            {"results": [{"data": [{"ratio": True}]}]},
            {"results": [{"data": [{"ratio": "12.3"}]}]},
            {"results": [{"data": [{"ratio": float("nan")}]}]},
            {"results": [{"data": [{"ratio": float("inf")}]}]},
            {"results": [{"data": [{"ratio": 10**400}]}]},
        ]

        for payload in payloads:
            with self.subTest(payload=payload):
                client = NaverClient(
                    self.config,
                    transport=lambda *args, payload=payload: payload,
                )
                with self.assertRaises(NaverAPIError):
                    client.datalab_search_trends(request)

    def test_default_transport_replaces_invalid_utf8_bytes(self) -> None:
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = b'{"note":"\xff"}'

        with mock.patch("naver_mcp.client.urllib.request.urlopen", return_value=response):
            payload = self.client._default_transport(
                "GET",
                "https://api.example.com/test",
                {},
                None,
                1.0,
            )

        self.assertEqual(payload["note"], "\ufffd")

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
