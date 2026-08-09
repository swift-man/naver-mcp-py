from __future__ import annotations

import inspect
import sys
import unittest
from pathlib import Path
from typing import Any, Callable
from unittest.mock import patch

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from naver_mcp.config import NaverMCPConfig
from naver_mcp.server import create_server


class FakeFastMCP:
    def __init__(self, name: str) -> None:
        self.name = name
        self.tools: dict[str, Callable[..., Any]] = {}

    def tool(self) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def register(function: Callable[..., Any]) -> Callable[..., Any]:
            self.tools[function.__name__] = function
            return function

        return register


class ServerContractTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
