from __future__ import annotations

import ipaddress
import math
import os
import urllib.parse
from dataclasses import dataclass
from typing import Mapping, Optional

from .errors import ValidationError

DEFAULT_API_BASE_URL = "https://naverapihub.apigw.ntruss.com"
HTTP_TRANSPORTS = {"http", "sse", "streamable-http"}
SUPPORTED_TRANSPORTS = HTTP_TRANSPORTS | {"stdio"}
REMOTE_ACCESS_MODES = {"disabled", "fastmcp-auth", "trusted-network"}


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


def _is_loopback_host(host: str) -> bool:
    normalized = host.strip().strip("[]")
    if normalized.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def _validate_api_base_url(value: object) -> str:
    if not isinstance(value, str):
        raise ValidationError(
            "api_base_url must be a valid HTTPS URL or loopback HTTP URL"
        )
    normalized = value.strip()
    try:
        parsed = urllib.parse.urlsplit(normalized)
        _ = parsed.port
    except ValueError as exc:
        raise ValidationError(
            "api_base_url must be a valid HTTPS URL or loopback HTTP URL"
        ) from exc
    if (
        not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValidationError(
            "api_base_url must be a valid HTTPS URL or loopback HTTP URL"
        )
    if parsed.scheme == "https":
        return normalized
    # 로컬 테스트 및 프록시 개발에만 평문 HTTP를 허용한다.
    if parsed.scheme == "http" and _is_loopback_host(parsed.hostname):
        return normalized
    raise ValidationError(
        "api_base_url must use HTTPS unless it targets a loopback host"
    )


def _validate_https_url(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a valid HTTPS URL")
    normalized = value.strip()
    try:
        parsed = urllib.parse.urlsplit(normalized)
        _ = parsed.port
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be a valid HTTPS URL") from exc
    if (
        normalized != value
        or parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or any(character.isspace() for character in normalized)
    ):
        raise ValidationError(f"{field_name} must be a valid HTTPS URL")
    return normalized


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
    remote_access: str = "disabled"
    auth_jwks_uri: str = ""
    auth_issuer: str = ""
    auth_audience: str = ""

    def __post_init__(self) -> None:
        if isinstance(self.port, bool) or not isinstance(self.port, int):
            raise ValidationError("port must be an integer between 1 and 65535")
        if not 1 <= self.port <= 65535:
            raise ValidationError("port must be an integer between 1 and 65535")
        if isinstance(self.cache_ttl_sec, bool) or not isinstance(
            self.cache_ttl_sec, int
        ):
            raise ValidationError("cache_ttl_sec must be a non-negative integer")
        if self.cache_ttl_sec < 0:
            raise ValidationError("cache_ttl_sec must be a non-negative integer")

        timeout = self.http_timeout_sec
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
            raise ValidationError("http_timeout_sec must be a finite positive number")
        try:
            normalized_timeout = float(timeout)
        except (OverflowError, ValueError) as exc:
            raise ValidationError(
                "http_timeout_sec must be a finite positive number"
            ) from exc
        if not math.isfinite(normalized_timeout) or normalized_timeout <= 0:
            raise ValidationError("http_timeout_sec must be a finite positive number")
        object.__setattr__(self, "http_timeout_sec", normalized_timeout)
        object.__setattr__(
            self,
            "api_base_url",
            _validate_api_base_url(self.api_base_url),
        )

        if not isinstance(self.transport, str):
            raise ValidationError("transport must be a string")
        transport = self.transport.strip().lower()
        if transport not in SUPPORTED_TRANSPORTS:
            allowed = ", ".join(sorted(SUPPORTED_TRANSPORTS))
            raise ValidationError(f"transport must be one of: {allowed}")
        object.__setattr__(self, "transport", transport)

        if not isinstance(self.remote_access, str):
            raise ValidationError("remote_access must be a string")
        remote_access = self.remote_access.strip().lower()
        if remote_access not in REMOTE_ACCESS_MODES:
            allowed = ", ".join(sorted(REMOTE_ACCESS_MODES))
            raise ValidationError(f"remote_access must be one of: {allowed}")
        object.__setattr__(self, "remote_access", remote_access)

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
            remote_access=(
                _read_str(source, "NAVER_MCP_REMOTE_ACCESS", "disabled")
                or "disabled"
            ),
            auth_jwks_uri=_read_str(source, "NAVER_MCP_AUTH_JWKS_URI"),
            auth_issuer=_read_str(source, "NAVER_MCP_AUTH_ISSUER"),
            auth_audience=_read_str(source, "NAVER_MCP_AUTH_AUDIENCE"),
        )

    def require_credentials(self) -> None:
        if self.client_id and self.client_secret:
            return
        raise ValidationError(
            "NAVER_API_HUB_CLIENT_ID and NAVER_API_HUB_CLIENT_SECRET must be configured"
        )

    def require_safe_remote_access(self) -> None:
        if self.remote_access == "fastmcp-auth":
            if self.auth_jwks_uri and self.auth_issuer and self.auth_audience:
                _validate_https_url(
                    self.auth_jwks_uri,
                    "NAVER_MCP_AUTH_JWKS_URI",
                )
                return
            raise ValidationError(
                "NAVER_MCP_AUTH_JWKS_URI, NAVER_MCP_AUTH_ISSUER, and "
                "NAVER_MCP_AUTH_AUDIENCE must be configured for fastmcp-auth"
            )
        if self.transport not in HTTP_TRANSPORTS or _is_loopback_host(self.host):
            return
        if self.remote_access == "trusted-network":
            return
        raise ValidationError(
            "non-loopback HTTP binding requires NAVER_MCP_REMOTE_ACCESS="
            "fastmcp-auth or trusted-network"
        )
