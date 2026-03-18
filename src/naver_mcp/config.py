from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping, Optional

from .errors import ValidationError


def _read_str(env: Mapping[str, str], key: str, default: str = "") -> str:
    return env.get(key, default).strip()


def _read_int(env: Mapping[str, str], key: str, default: int) -> int:
    raw = env.get(key)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValidationError(f"{key} must be an integer") from exc


def _read_float(env: Mapping[str, str], key: str, default: float) -> float:
    raw = env.get(key)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValidationError(f"{key} must be a float") from exc


@dataclass(frozen=True)
class NaverMCPConfig:
    client_id: str = ""
    client_secret: str = ""
    host: str = "127.0.0.1"
    port: int = 8100
    path: str = "/mcp"
    transport: str = "streamable-http"
    http_timeout_sec: float = 8.0
    cache_ttl_sec: int = 300
    api_base_url: str = "https://openapi.naver.com/v1"

    @classmethod
    def from_env(
        cls,
        env: Optional[Mapping[str, str]] = None,
    ) -> "NaverMCPConfig":
        source = env or os.environ
        return cls(
            client_id=_read_str(source, "NAVER_CLIENT_ID"),
            client_secret=_read_str(source, "NAVER_CLIENT_SECRET"),
            host=_read_str(source, "NAVER_MCP_HOST", "127.0.0.1"),
            port=_read_int(source, "NAVER_MCP_PORT", 8100),
            path=_read_str(source, "NAVER_MCP_PATH", "/mcp") or "/mcp",
            transport=_read_str(
                source,
                "NAVER_MCP_TRANSPORT",
                "streamable-http",
            ),
            http_timeout_sec=_read_float(source, "NAVER_HTTP_TIMEOUT_SEC", 8.0),
            cache_ttl_sec=_read_int(source, "NAVER_CACHE_TTL_SEC", 300),
        )

    def require_credentials(self) -> None:
        if self.client_id and self.client_secret:
            return
        raise ValidationError(
            "NAVER_CLIENT_ID and NAVER_CLIENT_SECRET must be configured"
        )
