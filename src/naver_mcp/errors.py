from __future__ import annotations

from dataclasses import dataclass
from typing import NoReturn, Optional


@dataclass(frozen=True)
class ErrorPayload:
    code: str
    message: str
    retryable: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "retryable": self.retryable,
            }
        }


class NaverMCPError(Exception):
    code = "NAVER_API_ERROR"
    retryable = False

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        code: Optional[str] = None,
        retryable: Optional[bool] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = code or self.code
        self.is_retryable = self.retryable if retryable is None else retryable

    def to_dict(self) -> dict[str, object]:
        return ErrorPayload(
            code=self.error_code,
            message=self.message,
            retryable=self.is_retryable,
        ).to_dict()


class ValidationError(NaverMCPError):
    code = "VALIDATION_ERROR"
    retryable = False


class NaverAuthError(NaverMCPError):
    code = "NAVER_AUTH_ERROR"
    retryable = False


class NaverRateLimitError(NaverMCPError):
    code = "NAVER_RATE_LIMIT"
    retryable = False


class NaverTimeoutError(NaverMCPError):
    code = "NAVER_TIMEOUT"
    retryable = True


class NaverAPIError(NaverMCPError):
    code = "NAVER_API_ERROR"
    retryable = False


class NaverServiceUnavailableError(NaverMCPError):
    code = "NAVER_SERVICE_UNAVAILABLE"
    retryable = False


RETIRED_SEARCH_NOTICE = (
    "book, shopping, and professional document search APIs on 2026-07-31"
)


def raise_retired_search(tool_name: str) -> NoReturn:
    raise NaverServiceUnavailableError(
        f"{tool_name} is unavailable because Naver ended the underlying "
        f"{RETIRED_SEARCH_NOTICE}"
    )
