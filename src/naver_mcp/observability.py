from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from .errors import NaverMCPError

LOGGER_NAME = "naver_mcp"
TOOL_LOGGER_NAME = f"{LOGGER_NAME}.tools"
_JSON_HANDLER_MARKER = "_naver_mcp_json_handler"
_SAFE_RECORD_FIELDS = (
    "request_id",
    "tool",
    "error_code",
    "retryable",
    "status_code",
)
_INFO_ERROR_CODES = {"VALIDATION_ERROR", "NAVER_SERVICE_UNAVAILABLE"}
_WARNING_ERROR_CODES = {
    "NAVER_AUTH_ERROR",
    "NAVER_RATE_LIMIT",
    "NAVER_TIMEOUT",
}


class JsonLogFormatter(logging.Formatter):
    """민감한 메시지를 제외한 운영 필드만 JSON으로 직렬화한다."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc)
        payload: dict[str, object] = {
            "timestamp": timestamp.isoformat(timespec="milliseconds").replace(
                "+00:00",
                "Z",
            ),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", "application_log"),
        }
        for field_name in _SAFE_RECORD_FIELDS:
            value = getattr(record, field_name, None)
            if value is not None:
                payload[field_name] = value
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_logging(log_level: str) -> None:
    """CLI 서버 로그를 systemd journal에 적합한 JSON 형식으로 설정한다."""

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(log_level)
    logger.propagate = False

    for handler in logger.handlers:
        if getattr(handler, _JSON_HANDLER_MARKER, False):
            handler.setLevel(log_level)
            return

    handler = logging.StreamHandler()
    handler.setLevel(log_level)
    handler.setFormatter(JsonLogFormatter())
    setattr(handler, _JSON_HANDLER_MARKER, True)
    logger.addHandler(handler)


def error_log_level(error: NaverMCPError) -> int:
    if error.error_code in _INFO_ERROR_CODES:
        return logging.INFO
    if error.error_code in _WARNING_ERROR_CODES or error.is_retryable:
        return logging.WARNING
    return logging.ERROR
