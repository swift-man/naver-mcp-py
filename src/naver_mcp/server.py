from __future__ import annotations

from typing import Any, Optional

from .cache import TTLCache
from .client import NaverClient
from .config import NaverMCPConfig
from .tools_datalab import DataLabTools
from .tools_search import SearchTools

try:
    from fastmcp import FastMCP
except ImportError:  # pragma: no cover - optional runtime dependency
    FastMCP = None  # type: ignore[assignment]


def create_server(config: Optional[NaverMCPConfig] = None) -> Any:
    if FastMCP is None:
        raise RuntimeError(
            "fastmcp is not installed. Install the optional 'server' dependency first."
        )

    # 서버는 요청 객체 생성과 도구 등록만 맡고, 실제 비즈니스 로직은 tools 계층으로 위임한다.
    resolved_config = config or NaverMCPConfig.from_env()
    client = NaverClient(resolved_config)
    search_tools = SearchTools(
        client,
        cache=TTLCache(default_ttl_sec=resolved_config.cache_ttl_sec),
        config=resolved_config,
    )
    datalab_tools = DataLabTools(client, config=resolved_config)

    server = FastMCP("naver-mcp-py")

    @server.tool()
    def search_local(
        query: str,
        display: int = 5,
        start: int = 1,
        sort: str = "random",
    ) -> dict[str, Any]:
        return search_tools.search_local(
            query=query,
            display=display,
            start=start,
            sort=sort,
        )

    @server.tool()
    def search_blog(
        query: str,
        display: int = 5,
        start: int = 1,
        sort: str = "sim",
    ) -> dict[str, Any]:
        return search_tools.search_blog(
            query=query,
            display=display,
            start=start,
            sort=sort,
        )

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
        return search_tools.search_news(
            query=query,
            display=display,
            start=start,
            sort=sort,
        )

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
    def spell_check(query: str) -> dict[str, Any]:
        return search_tools.spell_check(query=query)

    @server.tool()
    def detect_adult_query(query: str) -> dict[str, Any]:
        return search_tools.detect_adult_query(query=query)

    @server.tool()
    def search_naver_auto(
        query: str,
        display: int = 5,
    ) -> dict[str, Any]:
        return search_tools.search_naver_auto(query=query, display=display)

    @server.tool()
    def datalab_search_trends(
        start_date: str,
        end_date: str,
        time_unit: str,
        keyword_groups: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return datalab_tools.datalab_search_trends(
            start_date=start_date,
            end_date=end_date,
            time_unit=time_unit,
            keyword_groups=keyword_groups,
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
    server = create_server(config)
    server.run(
        transport=config.transport,
        host=config.host,
        port=config.port,
        path=config.path,
    )


if __name__ == "__main__":
    main()
