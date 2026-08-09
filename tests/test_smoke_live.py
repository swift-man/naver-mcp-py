from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from naver_mcp.client import NaverClient
from naver_mcp.config import NaverMCPConfig
from naver_mcp.models import BlogSearchRequest


@unittest.skipUnless(
    os.environ.get("NAVER_LIVE_SMOKE_TEST") == "1",
    "set NAVER_LIVE_SMOKE_TEST=1 to call the real NAVER API HUB",
)
class NaverAPIHubLiveSmokeTest(unittest.TestCase):
    def test_blog_search(self) -> None:
        config = NaverMCPConfig.from_env()
        config.require_credentials()
        result = NaverClient(config).search_blog(
            BlogSearchRequest(query="네이버", display=1, start=1)
        )

        self.assertIn("items", result)
        self.assertIsInstance(result["items"], list)


if __name__ == "__main__":
    unittest.main()
