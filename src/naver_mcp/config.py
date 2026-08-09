from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping, Optional

from .errors import ValidationError

DEFAULT_API_BASE_URL = "https://naverapihub.apigw.ntruss.com"


def _read_str(env: Mapping[str, str], key: str, default: str = "") -> str:
    return env.get(key, default).strip()


def _read_credentials(env: Mapping[str, str]) -> tuple[str, str]:
    hub_credentials = (
        _read_str(env, "NAVER_API_HUB_CLIENT_ID"),
        _read_str(env, "NAVER_API_HUB_CLIENT_SECRET"),
    )
    # 신규 자격 증명이 일부라도 설정되면 레거시 값과 섞지 않고 신규 쌍만 사용한다.
    if any(hub_credentials):
        return hub_credentials
    return (
        _read_str(env, "NAVER_CLIENT_ID"),
        _read_str(env, "NAVER_CLIENT_SECRET"),
    )


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
    api_base_url: str = DEFAULT_API_BASE_URL

    @classmethod
    def from_env(
        cls,
        env: Optional[Mapping[str, str]] = None,
    ) -> "NaverMCPConfig":
        source = os.environ if env is None else env
        client_id, client_secret = _read_credentials(source)
        return cls(
            client_id=client_id,
            client_secret=client_secret,
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
            api_base_url=(
                _read_str(source, "NAVER_API_BASE_URL", DEFAULT_API_BASE_URL)
                or DEFAULT_API_BASE_URL
            ),
        )

    def require_credentials(self) -> None:
        if self.client_id and self.client_secret:
            return
        raise ValidationError(
            "NAVER_API_HUB_CLIENT_ID and NAVER_API_HUB_CLIENT_SECRET must be configured"
        )
