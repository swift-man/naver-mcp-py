from __future__ import annotations

import inspect
import io
import json
import logging
import sys
import unittest
from pathlib import Path
from typing import Any, Callable
from unittest.mock import Mock, patch

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from naver_mcp.config import NaverMCPConfig
from naver_mcp.errors import (
    NaverAPIError,
    NaverAuthError,
    NaverRateLimitError,
    NaverServiceUnavailableError,
    NaverTimeoutError,
    ValidationError,
)
from naver_mcp.observability import JsonLogFormatter, configure_logging
from naver_mcp.server import _ToolErrorBoundary, create_server, main


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


class RecordingLogHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


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
        self.assertRegex(result["meta"]["request_id"], r"^[0-9a-f]{32}$")

    def test_tool_error_logging_uses_safe_structured_fields_and_levels(self) -> None:
        class FailingTools:
            def __init__(self, error: Exception) -> None:
                self.error = error

            def fail(self, query: str) -> None:
                raise self.error

        cases = [
            (ValidationError("secret query"), logging.INFO),
            (NaverServiceUnavailableError("retired"), logging.INFO),
            (NaverAuthError("secret credential", status_code=401), logging.WARNING),
            (NaverRateLimitError("quota", status_code=429), logging.WARNING),
            (NaverTimeoutError("timeout"), logging.WARNING),
            (NaverAPIError("temporary", retryable=True), logging.WARNING),
            (NaverAPIError("invalid upstream payload"), logging.ERROR),
        ]
        logger = logging.getLogger("naver_mcp.tools")
        original_level = logger.level
        original_propagate = logger.propagate
        handler = RecordingLogHandler()
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        logger.addHandler(handler)
        try:
            for error, expected_level in cases:
                with self.subTest(error=error.error_code):
                    handler.records.clear()
                    result = _ToolErrorBoundary(FailingTools(error)).fail(
                        "never-log-this-query"
                    )

                    self.assertEqual(len(handler.records), 1)
                    record = handler.records[0]
                    request_id = result["meta"]["request_id"]
                    self.assertEqual(record.levelno, expected_level)
                    self.assertEqual(record.getMessage(), "tool_error")
                    self.assertEqual(record.event, "tool_error")
                    self.assertEqual(record.tool, "fail")
                    self.assertEqual(record.error_code, error.error_code)
                    self.assertEqual(record.retryable, error.is_retryable)
                    self.assertEqual(record.request_id, request_id)
                    self.assertNotIn("never-log-this-query", record.getMessage())
                    self.assertNotIn(error.message, record.getMessage())
        finally:
            logger.removeHandler(handler)
            logger.setLevel(original_level)
            logger.propagate = original_propagate

    def test_json_log_formatter_emits_only_allowlisted_fields(self) -> None:
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JsonLogFormatter())
        logger = logging.getLogger("naver_mcp.formatter-test")
        original_level = logger.level
        original_propagate = logger.propagate
        logger.setLevel(logging.INFO)
        logger.propagate = False
        logger.addHandler(handler)
        try:
            logger.info(
                "message-that-must-not-be-serialized",
                extra={
                    "event": "tool_error",
                    "request_id": "a" * 32,
                    "tool": "search_local",
                    "error_code": "VALIDATION_ERROR",
                    "retryable": False,
                    "client_secret": "never-serialize-this",
                },
            )
        finally:
            logger.removeHandler(handler)
            logger.setLevel(original_level)
            logger.propagate = original_propagate

        payload = json.loads(stream.getvalue())
        self.assertEqual(payload["event"], "tool_error")
        self.assertEqual(payload["request_id"], "a" * 32)
        self.assertEqual(payload["tool"], "search_local")
        self.assertEqual(payload["error_code"], "VALIDATION_ERROR")
        self.assertFalse(payload["retryable"])
        self.assertRegex(payload["timestamp"], r"^\d{4}-\d{2}-\d{2}T.*Z$")
        self.assertNotIn("message", payload)
        self.assertNotIn("client_secret", payload)
        self.assertNotIn("message-that-must-not-be-serialized", stream.getvalue())

        stream.seek(0)
        stream.truncate(0)
        handler.emit(
            logging.LogRecord(
                "naver_mcp.formatter-test",
                logging.INFO,
                __file__,
                1,
                "another-sensitive-message",
                (),
                None,
            )
        )
        fallback_payload = json.loads(stream.getvalue())
        self.assertEqual(fallback_payload["event"], "application_log")
        self.assertNotIn("another-sensitive-message", stream.getvalue())

    def test_configure_logging_is_idempotent(self) -> None:
        logger = logging.getLogger("naver_mcp")
        original_handlers = list(logger.handlers)
        original_level = logger.level
        original_propagate = logger.propagate
        logger.handlers.clear()
        try:
            configure_logging("INFO")
            configure_logging("ERROR")

            self.assertEqual(len(logger.handlers), 1)
            self.assertIsInstance(logger.handlers[0].formatter, JsonLogFormatter)
            self.assertEqual(logger.level, logging.ERROR)
            self.assertEqual(logger.handlers[0].level, logging.ERROR)
            self.assertFalse(logger.propagate)
        finally:
            logger.handlers[:] = original_handlers
            logger.setLevel(original_level)
            logger.propagate = original_propagate

    def test_configured_tool_logger_emits_json(self) -> None:
        logger = logging.getLogger("naver_mcp")
        tool_logger = logging.getLogger("naver_mcp.tools")
        original_handlers = list(logger.handlers)
        original_level = logger.level
        original_propagate = logger.propagate
        original_tool_level = tool_logger.level
        original_tool_propagate = tool_logger.propagate
        logger.handlers.clear()
        stream = io.StringIO()
        try:
            configure_logging("INFO")
            logger.handlers[0].setStream(stream)
            tool_logger.setLevel(logging.NOTSET)
            tool_logger.propagate = True
            tool_logger.warning(
                "tool_error",
                extra={
                    "event": "tool_error",
                    "request_id": "b" * 32,
                    "tool": "search_news",
                    "error_code": "NAVER_TIMEOUT",
                    "retryable": True,
                },
            )
        finally:
            logger.handlers[:] = original_handlers
            logger.setLevel(original_level)
            logger.propagate = original_propagate
            tool_logger.setLevel(original_tool_level)
            tool_logger.propagate = original_tool_propagate

        payload = json.loads(stream.getvalue())
        self.assertEqual(payload["logger"], "naver_mcp.tools")
        self.assertEqual(payload["event"], "tool_error")
        self.assertEqual(payload["request_id"], "b" * 32)
        self.assertEqual(payload["error_code"], "NAVER_TIMEOUT")
        self.assertTrue(payload["retryable"])

    def test_main_passes_only_transport_for_stdio(self) -> None:
        config = NaverMCPConfig(transport="stdio")
        server = Mock()

        with (
            patch("naver_mcp.server.NaverMCPConfig.from_env", return_value=config),
            patch("naver_mcp.server.configure_logging") as configure_logging_mock,
            patch("naver_mcp.server.create_server", return_value=server),
        ):
            main()

        configure_logging_mock.assert_called_once_with("INFO")
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
            patch("naver_mcp.server.configure_logging") as configure_logging_mock,
            patch("naver_mcp.server.create_server", return_value=server),
        ):
            main()

        configure_logging_mock.assert_called_once_with("INFO")
        server.run.assert_called_once_with(
            transport="http",
            host="127.0.0.1",
            port=8100,
            path="/naver_mcp",
        )


if __name__ == "__main__":
    unittest.main()
