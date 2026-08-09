from __future__ import annotations

import inspect
import sys
import unittest
from pathlib import Path
from typing import Any, Callable
from unittest.mock import Mock, patch

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from naver_mcp.config import NaverMCPConfig
from naver_mcp.errors import ValidationError
from naver_mcp.server import create_server, main


class FakeFastMCP:
    def __init__(
        self,
        name: str,
        *,
        auth: Any = None,
        strict_input_validation: bool = False,
    ) -> None:
        self.name = name
        self.auth = auth
        self.strict_input_validation = strict_input_validation
        self.tools: dict[str, Callable[..., Any]] = {}

    def tool(self) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def register(function: Callable[..., Any]) -> Callable[..., Any]:
            self.tools[function.__name__] = function
            return function

        return register


class FakeJWTVerifier:
    def __init__(self, **config: Any) -> None:
        self.config = config


class ServerContractTest(unittest.TestCase):
    def test_create_server_refuses_unprotected_remote_http_binding(self) -> None:
        config = NaverMCPConfig(
            client_id="client-id",
            client_secret="client-secret",
            host="0.0.0.0",
        )

        with patch("naver_mcp.server.FastMCP", FakeFastMCP):
            with self.assertRaises(ValidationError):
                create_server(config)

    def test_remote_http_binding_accepts_declared_protection(self) -> None:
        protected_configs = [
            NaverMCPConfig(host="0.0.0.0", remote_access="trusted-network"),
            NaverMCPConfig(
                host="0.0.0.0",
                remote_access="fastmcp-auth",
                auth_jwks_uri="https://auth.example.com/.well-known/jwks.json",
                auth_issuer="https://auth.example.com",
                auth_audience="naver-mcp",
            ),
        ]

        for config in protected_configs:
            with self.subTest(remote_access=config.remote_access):
                config.require_safe_remote_access()

    def test_fastmcp_auth_mode_requires_jwt_configuration(self) -> None:
        for host in ("127.0.0.1", "0.0.0.0"):
            with self.subTest(host=host), self.assertRaises(ValidationError):
                config = NaverMCPConfig(host=host, remote_access="fastmcp-auth")
                config.require_safe_remote_access()

    def test_fastmcp_auth_mode_requires_valid_https_jwks(self) -> None:
        invalid_values = [
            "http://auth.example.com/.well-known/jwks.json",
            "https://[::1",
            "https://auth.example.com:99999/.well-known/jwks.json",
            "https://user:password@auth.example.com/.well-known/jwks.json",
            "https://auth.example.com/.well-known/jwks.json#fragment",
            "https://auth.example.com/jwks file.json",
            " https://auth.example.com/.well-known/jwks.json",
        ]

        for value in invalid_values:
            config = NaverMCPConfig(
                host="0.0.0.0",
                remote_access="fastmcp-auth",
                auth_jwks_uri=value,
                auth_issuer="https://auth.example.com",
                auth_audience="naver-mcp",
            )
            with self.subTest(value=value), self.assertRaises(ValidationError):
                config.require_safe_remote_access()

    def test_create_server_attaches_jwt_verifier(self) -> None:
        config = NaverMCPConfig(
            host="0.0.0.0",
            remote_access="fastmcp-auth",
            auth_jwks_uri="https://auth.example.com/.well-known/jwks.json",
            auth_issuer="https://auth.example.com",
            auth_audience="naver-mcp",
        )

        with (
            patch("naver_mcp.server.FastMCP", FakeFastMCP),
            patch("naver_mcp.server.JWTVerifier", FakeJWTVerifier),
        ):
            server = create_server(config)

        self.assertEqual(
            server.auth.config,
            {
                "jwks_uri": "https://auth.example.com/.well-known/jwks.json",
                "issuer": "https://auth.example.com",
                "audience": "naver-mcp",
            },
        )
        self.assertTrue(server.strict_input_validation)

    def test_all_search_and_datalab_tools_are_registered(self) -> None:
        with patch("naver_mcp.server.FastMCP", FakeFastMCP):
            server = create_server(
                NaverMCPConfig(client_id="client-id", client_secret="client-secret")
            )

        self.assertEqual(
            set(server.tools),
            {
                "search_local",
                "search_blog",
                "search_web",
                "search_news",
                "search_cafearticle",
                "search_image",
                "search_book",
                "search_book_advanced",
                "search_encyc",
                "search_kin",
                "search_shop",
                "search_doc",
                "spell_check",
                "detect_adult_query",
                "search_naver_auto",
                "datalab_search_trends",
                "datalab_shopping_category_trends",
                "datalab_shopping_category_device_trends",
                "datalab_shopping_category_gender_trends",
                "datalab_shopping_category_age_trends",
                "datalab_shopping_keyword_trends",
                "datalab_shopping_keyword_device_trends",
                "datalab_shopping_keyword_gender_trends",
                "datalab_shopping_keyword_age_trends",
                "datalab_shopping_device_trends",
            },
        )

    def test_search_trend_tool_exposes_api_hub_filters(self) -> None:
        with patch("naver_mcp.server.FastMCP", FakeFastMCP):
            server = create_server(
                NaverMCPConfig(client_id="client-id", client_secret="client-secret")
            )

        parameters = inspect.signature(server.tools["datalab_search_trends"]).parameters
        self.assertIn("device", parameters)
        self.assertIn("gender", parameters)
        self.assertIn("ages", parameters)

    def test_retired_tools_remain_visible_with_explanatory_descriptions(self) -> None:
        with patch("naver_mcp.server.FastMCP", FakeFastMCP):
            server = create_server(
                NaverMCPConfig(client_id="client-id", client_secret="client-secret")
            )

        for name in ("search_book", "search_book_advanced", "search_shop", "search_doc"):
            description = server.tools[name].__doc__ or ""
            self.assertIn("지원 종료", description)
            self.assertIn("항상 NAVER_SERVICE_UNAVAILABLE", description)
            self.assertIn("사용하세요", description)

    def test_retired_tool_returns_structured_error(self) -> None:
        with patch("naver_mcp.server.FastMCP", FakeFastMCP):
            server = create_server(
                NaverMCPConfig(client_id="client-id", client_secret="client-secret")
            )

        retired_calls = [
            lambda: server.tools["search_book"]("파이썬"),
            lambda: server.tools["search_book_advanced"](title="클린 코드"),
            lambda: server.tools["search_shop"]("무선 이어폰"),
            lambda: server.tools["search_doc"]("생성형 AI"),
        ]

        for call in retired_calls:
            with self.subTest(call=call):
                result = call()
                self.assertEqual(result["error"]["code"], "NAVER_SERVICE_UNAVAILABLE")
                self.assertFalse(result["error"]["retryable"])

    def test_validation_error_returns_structured_error(self) -> None:
        with patch("naver_mcp.server.FastMCP", FakeFastMCP):
            server = create_server(
                NaverMCPConfig(client_id="client-id", client_secret="client-secret")
            )

        result = server.tools["search_local"]("판교 맛집", display=6)

        self.assertEqual(result["error"]["code"], "VALIDATION_ERROR")
        self.assertFalse(result["error"]["retryable"])

    def test_main_passes_only_transport_for_stdio(self) -> None:
        config = NaverMCPConfig(transport="stdio")
        server = Mock()

        with (
            patch("naver_mcp.server.NaverMCPConfig.from_env", return_value=config),
            patch("naver_mcp.server.create_server", return_value=server),
        ):
            main()

        server.run.assert_called_once_with(transport="stdio")

    def test_main_passes_network_options_for_http_transport(self) -> None:
        config = NaverMCPConfig(
            transport="http",
            host="127.0.0.1",
            port=8100,
            path="/naver_mcp",
        )
        server = Mock()

        with (
            patch("naver_mcp.server.NaverMCPConfig.from_env", return_value=config),
            patch("naver_mcp.server.create_server", return_value=server),
        ):
            main()

        server.run.assert_called_once_with(
            transport="http",
            host="127.0.0.1",
            port=8100,
            path="/naver_mcp",
        )


if __name__ == "__main__":
    unittest.main()
