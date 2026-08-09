from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from .cache import TTLCache
from .client import NaverClient
from .config import NaverMCPConfig
from .errors import NaverMCPError
from .observability import TOOL_LOGGER_NAME, configure_logging, error_log_level
from .tools_datalab import DataLabTools
from .tools_search import SearchTools

try:
    from fastmcp import FastMCP
    from fastmcp.server.auth.providers.jwt import JWTVerifier
except ImportError:  # pragma: no cover - optional runtime dependency
    FastMCP = None  # type: ignore[assignment]
    JWTVerifier = None  # type: ignore[assignment]


class _ToolErrorBoundary:
    def __init__(self, tools: Any) -> None:
        self._tools = tools
        self._logger = logging.getLogger(TOOL_LOGGER_NAME)

    def __getattr__(self, name: str) -> Any:
        tool = getattr(self._tools, name)
        if not callable(tool):
            return tool

        def call(*args: Any, **kwargs: Any) -> Any:
            try:
                return tool(*args, **kwargs)
            except NaverMCPError as exc:
                request_id = uuid.uuid4().hex
                # 입력값과 오류 메시지는 기록하지 않고 운영 분기에 필요한 필드만 남긴다.
                self._logger.log(
                    error_log_level(exc),
                    "tool_error",
                    extra={
                        "event": "tool_error",
                        "request_id": request_id,
                        "tool": name,
                        "error_code": exc.error_code,
                        "retryable": exc.is_retryable,
                        "status_code": exc.status_code,
                    },
                )
                # 응답과 서버 로그를 연결하되 기존 오류 객체는 그대로 유지한다.
                payload = exc.to_dict()
                payload["meta"] = {"request_id": request_id}
                return payload

        return call


def create_server(config: Optional[NaverMCPConfig] = None) -> Any:
    if FastMCP is None:
        raise RuntimeError(
            "fastmcp is not installed. Install the optional 'server' dependency first."
        )

    # 서버는 요청 객체 생성과 도구 등록만 맡고, 실제 비즈니스 로직은 tools 계층으로 위임한다.
    resolved_config = config or NaverMCPConfig.from_env()
    # 원격 HTTP 바인딩은 인증 또는 운영자가 확인한 네트워크 보호 없이는 허용하지 않는다.
    resolved_config.require_safe_remote_access()
    client = NaverClient(resolved_config)
    search_tools = _ToolErrorBoundary(
        SearchTools(
            client,
            cache=TTLCache(default_ttl_sec=resolved_config.cache_ttl_sec),
            config=resolved_config,
        )
    )
    datalab_tools = _ToolErrorBoundary(DataLabTools(client, config=resolved_config))

    auth = None
    if resolved_config.remote_access == "fastmcp-auth":
        if JWTVerifier is None:  # pragma: no cover - FastMCP import guard handles this
            raise RuntimeError("FastMCP JWT authentication is not available")
        auth = JWTVerifier(
            jwks_uri=resolved_config.auth_jwks_uri,
            issuer=resolved_config.auth_issuer,
            audience=resolved_config.auth_audience,
        )

    server = FastMCP(
        "naver-mcp-py",
        auth=auth,
        strict_input_validation=True,
    )

    @server.tool()
    def search_local(
        query: str,
        display: int = 5,
        start: int = 1,
        sort: str = "random",
    ) -> dict[str, Any]:
        return search_tools.search_local(query=query, display=display, start=start, sort=sort)

    @server.tool()
    def search_blog(
        query: str,
        display: int = 5,
        start: int = 1,
        sort: str = "sim",
    ) -> dict[str, Any]:
        return search_tools.search_blog(query=query, display=display, start=start, sort=sort)

    @server.tool()
    def search_web(
        query: str,
        display: int = 5,
        start: int = 1,
    ) -> dict[str, Any]:
        return search_tools.search_web(query=query, display=display, start=start)

    @server.tool()
    def search_news(
        query: str,
        display: int = 5,
        start: int = 1,
        sort: str = "sim",
    ) -> dict[str, Any]:
        return search_tools.search_news(query=query, display=display, start=start, sort=sort)

    @server.tool()
    def search_cafearticle(
        query: str,
        display: int = 5,
        start: int = 1,
        sort: str = "sim",
    ) -> dict[str, Any]:
        return search_tools.search_cafearticle(
            query=query,
            display=display,
            start=start,
            sort=sort,
        )

    @server.tool()
    def search_image(
        query: str,
        display: int = 5,
        start: int = 1,
        sort: str = "sim",
        filter: str = "all",
    ) -> dict[str, Any]:
        return search_tools.search_image(
            query=query,
            display=display,
            start=start,
            sort=sort,
            filter=filter,
        )

    @server.tool()
    def search_book(
        query: str,
        display: int = 5,
        start: int = 1,
        sort: str = "sim",
    ) -> dict[str, Any]:
        """[지원 종료] 항상 NAVER_SERVICE_UNAVAILABLE 오류를 반환합니다.

        도서 검색은 search_web 또는 search_naver_auto를 사용하세요.
        """
        return search_tools.search_book(query=query, display=display, start=start, sort=sort)

    @server.tool()
    def search_book_advanced(
        query: str = "",
        display: int = 5,
        start: int = 1,
        sort: str = "sim",
        title: str = "",
        isbn: str = "",
    ) -> dict[str, Any]:
        """[지원 종료] 항상 NAVER_SERVICE_UNAVAILABLE 오류를 반환합니다.

        도서 검색은 search_web 또는 search_naver_auto를 사용하세요.
        """
        return search_tools.search_book_advanced(
            query=query,
            display=display,
            start=start,
            sort=sort,
            title=title,
            isbn=isbn,
        )

    @server.tool()
    def search_encyc(
        query: str,
        display: int = 5,
        start: int = 1,
    ) -> dict[str, Any]:
        return search_tools.search_encyc(query=query, display=display, start=start)

    @server.tool()
    def search_kin(
        query: str,
        display: int = 5,
        start: int = 1,
        sort: str = "sim",
    ) -> dict[str, Any]:
        return search_tools.search_kin(query=query, display=display, start=start, sort=sort)

    @server.tool()
    def search_shop(
        query: str,
        display: int = 5,
        start: int = 1,
        sort: str = "sim",
        filter: str = "",
        exclude: str = "",
    ) -> dict[str, Any]:
        """[지원 종료] 항상 NAVER_SERVICE_UNAVAILABLE 오류를 반환합니다.

        상품 검색은 search_web 또는 search_naver_auto를 사용하세요.
        """
        return search_tools.search_shop(
            query=query,
            display=display,
            start=start,
            sort=sort,
            filter=filter,
            exclude=exclude,
        )

    @server.tool()
    def search_doc(
        query: str,
        display: int = 5,
        start: int = 1,
    ) -> dict[str, Any]:
        """[지원 종료] 항상 NAVER_SERVICE_UNAVAILABLE 오류를 반환합니다.

        전문자료 검색은 search_web을 사용하세요.
        """
        return search_tools.search_doc(query=query, display=display, start=start)

    @server.tool()
    def spell_check(query: str) -> dict[str, Any]:
        return search_tools.spell_check(query=query)

    @server.tool()
    def detect_adult_query(query: str) -> dict[str, Any]:
        return search_tools.detect_adult_query(query=query)

    @server.tool()
    def search_naver_auto(query: str, display: int = 5) -> dict[str, Any]:
        return search_tools.search_naver_auto(query=query, display=display)

    @server.tool()
    def datalab_search_trends(
        start_date: str,
        end_date: str,
        time_unit: str,
        keyword_groups: list[dict[str, Any]],
        device: str = "",
        gender: str = "",
        ages: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        return datalab_tools.datalab_search_trends(
            start_date=start_date,
            end_date=end_date,
            time_unit=time_unit,
            keyword_groups=keyword_groups,
            device=device,
            gender=gender,
            ages=ages,
        )

    @server.tool()
    def datalab_shopping_category_trends(
        start_date: str,
        end_date: str,
        time_unit: str,
        categories: list[dict[str, Any]],
        device: str = "",
        gender: str = "",
        ages: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        return datalab_tools.datalab_shopping_category_trends(
            start_date=start_date,
            end_date=end_date,
            time_unit=time_unit,
            categories=categories,
            device=device,
            gender=gender,
            ages=ages,
        )

    @server.tool()
    def datalab_shopping_category_device_trends(
        start_date: str,
        end_date: str,
        time_unit: str,
        category: str,
        device: str = "",
        gender: str = "",
        ages: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        return datalab_tools.datalab_shopping_category_device_trends(
            start_date=start_date,
            end_date=end_date,
            time_unit=time_unit,
            category=category,
            device=device,
            gender=gender,
            ages=ages,
        )

    @server.tool()
    def datalab_shopping_category_gender_trends(
        start_date: str,
        end_date: str,
        time_unit: str,
        category: str,
        device: str = "",
        gender: str = "",
        ages: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        return datalab_tools.datalab_shopping_category_gender_trends(
            start_date=start_date,
            end_date=end_date,
            time_unit=time_unit,
            category=category,
            device=device,
            gender=gender,
            ages=ages,
        )

    @server.tool()
    def datalab_shopping_category_age_trends(
        start_date: str,
        end_date: str,
        time_unit: str,
        category: str,
        device: str = "",
        gender: str = "",
        ages: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        return datalab_tools.datalab_shopping_category_age_trends(
            start_date=start_date,
            end_date=end_date,
            time_unit=time_unit,
            category=category,
            device=device,
            gender=gender,
            ages=ages,
        )

    @server.tool()
    def datalab_shopping_keyword_trends(
        start_date: str,
        end_date: str,
        time_unit: str,
        category: str,
        keywords: list[dict[str, Any]],
        device: str = "",
        gender: str = "",
        ages: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        return datalab_tools.datalab_shopping_keyword_trends(
            start_date=start_date,
            end_date=end_date,
            time_unit=time_unit,
            category=category,
            keywords=keywords,
            device=device,
            gender=gender,
            ages=ages,
        )

    @server.tool()
    def datalab_shopping_keyword_device_trends(
        start_date: str,
        end_date: str,
        time_unit: str,
        category: str,
        keyword: str,
        device: str = "",
        gender: str = "",
        ages: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        return datalab_tools.datalab_shopping_keyword_device_trends(
            start_date=start_date,
            end_date=end_date,
            time_unit=time_unit,
            category=category,
            keyword=keyword,
            device=device,
            gender=gender,
            ages=ages,
        )

    @server.tool()
    def datalab_shopping_keyword_gender_trends(
        start_date: str,
        end_date: str,
        time_unit: str,
        category: str,
        keyword: str,
        device: str = "",
        gender: str = "",
        ages: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        return datalab_tools.datalab_shopping_keyword_gender_trends(
            start_date=start_date,
            end_date=end_date,
            time_unit=time_unit,
            category=category,
            keyword=keyword,
            device=device,
            gender=gender,
            ages=ages,
        )

    @server.tool()
    def datalab_shopping_keyword_age_trends(
        start_date: str,
        end_date: str,
        time_unit: str,
        category: str,
        keyword: str,
        device: str = "",
        gender: str = "",
        ages: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        return datalab_tools.datalab_shopping_keyword_age_trends(
            start_date=start_date,
            end_date=end_date,
            time_unit=time_unit,
            category=category,
            keyword=keyword,
            device=device,
            gender=gender,
            ages=ages,
        )

    # 기존 이름과의 호환성을 위해 category/device 엔드포인트를 별칭으로 유지한다.
    @server.tool()
    def datalab_shopping_device_trends(
        start_date: str,
        end_date: str,
        time_unit: str,
        category: str,
        device: str = "",
        gender: str = "",
        ages: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        return datalab_tools.datalab_shopping_device_trends(
            start_date=start_date,
            end_date=end_date,
            time_unit=time_unit,
            category=category,
            device=device,
            gender=gender,
            ages=ages,
        )

    return server


def healthz() -> dict[str, str]:
    # 별도 HTTP 래퍼를 둘 때 재사용할 수 있는 가장 단순한 헬스 체크 응답이다.
    return {"status": "ok"}


def main() -> None:
    config = NaverMCPConfig.from_env()
    configure_logging(config.log_level)
    server = create_server(config)
    if config.transport == "stdio":
        server.run(transport=config.transport)
        return
    server.run(
        transport=config.transport,
        host=config.host,
        port=config.port,
        path=config.path,
    )


if __name__ == "__main__":
    main()
