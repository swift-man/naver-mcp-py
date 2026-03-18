from __future__ import annotations

from collections.abc import Iterable
import html
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Mapping, Optional

KST = timezone(timedelta(hours=9))
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


def strip_html(value: Any) -> str:
    if value is None:
        return ""
    # Naver 응답은 <b> 강조 태그가 자주 섞여 있으므로 공통 전처리로 제거한다.
    text = html.unescape(str(value))
    text = _HTML_TAG_RE.sub(" ", text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def normalize_published_at(value: Any) -> Optional[str]:
    text = strip_html(value)
    if not text:
        return None

    # 뉴스 pubDate 같은 RFC822 형식을 먼저 처리한다.
    try:
        parsed = parsedate_to_datetime(text)
    except (TypeError, ValueError, IndexError):
        parsed = None
    if parsed is not None:
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=KST)
        return parsed.isoformat()

    # 블로그 postdate 같은 숫자형 날짜 포맷도 순서대로 흡수한다.
    for fmt in ("%Y%m%d%H%M%S", "%Y%m%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.replace(tzinfo=KST).isoformat()
        except ValueError:
            continue
    return text


def normalize_search_item(source: str, item: Mapping[str, Any]) -> dict[str, Any]:
    title = strip_html(item.get("title") or item.get("name"))
    snippet = strip_html(item.get("description") or item.get("snippet"))
    normalized: dict[str, Any] = {
        "title": title,
        "link": str(item.get("link") or ""),
        "snippet": snippet,
        "source": source,
        "published_at": normalize_published_at(
            item.get("pubDate") or item.get("pubdate") or item.get("postdate")
        ),
        "score": 0.0,
    }

    if source == "local":
        # 지역 검색은 공통 필드 외에도 지도/주소 계열 필드를 유지해 주는 편이 활용도가 높다.
        normalized.update(
            {
                "name": title,
                "category": strip_html(item.get("category")),
                "address": strip_html(item.get("address")),
                "road_address": strip_html(item.get("roadAddress")),
                "telephone": strip_html(item.get("telephone")),
                "mapx": str(item.get("mapx") or ""),
                "mapy": str(item.get("mapy") or ""),
            }
        )
        return normalized

    if source == "image":
        normalized.update(
            {
                "thumbnail": str(item.get("thumbnail") or ""),
                "size_height": str(item.get("sizeheight") or ""),
                "size_width": str(item.get("sizewidth") or ""),
            }
        )
        return normalized

    if source == "book":
        normalized.update(
            {
                "image": str(item.get("image") or ""),
                "author": strip_html(item.get("author")),
                "discount": str(item.get("discount") or ""),
                "publisher": strip_html(item.get("publisher")),
                "isbn": str(item.get("isbn") or ""),
            }
        )
        if "description" in item:
            normalized["description"] = snippet
        return normalized

    if source == "shop":
        normalized.update(
            {
                "image": str(item.get("image") or ""),
                "low_price": str(item.get("lprice") or ""),
                "high_price": str(item.get("hprice") or ""),
                "mall_name": strip_html(item.get("mallName")),
                "product_id": str(item.get("productId") or ""),
                "product_type": str(item.get("productType") or ""),
                "brand": strip_html(item.get("brand")),
                "maker": strip_html(item.get("maker")),
                "category1": strip_html(item.get("category1")),
                "category2": strip_html(item.get("category2")),
                "category3": strip_html(item.get("category3")),
                "category4": strip_html(item.get("category4")),
            }
        )
        return normalized

    if source == "encyc":
        normalized["thumbnail"] = str(item.get("thumbnail") or "")
        if "description" in item:
            normalized["description"] = snippet
        return normalized

    if item.get("originallink"):
        normalized["originallink"] = str(item["originallink"])
    if item.get("bloggername"):
        normalized["blogger_name"] = strip_html(item["bloggername"])
    if item.get("bloggerlink"):
        normalized["blogger_link"] = str(item["bloggerlink"])
    if item.get("cafename"):
        normalized["cafe_name"] = strip_html(item["cafename"])
    if item.get("cafeurl"):
        normalized["cafe_url"] = str(item["cafeurl"])
    if "description" in item:
        normalized["description"] = snippet
    return normalized


def normalize_search_response(
    query: str,
    source: str,
    payload: Mapping[str, Any],
    *,
    display: int,
    start: int,
    cached: bool = False,
) -> dict[str, Any]:
    raw_items = payload.get("items", [])
    items = [
        normalize_search_item(source, item)
        for item in raw_items
        if isinstance(item, Mapping)
    ]
    resolved_total = int(payload.get("total", len(items)) or 0)
    resolved_start = int(payload.get("start", start) or start)
    resolved_display = int(payload.get("display", display) or display)
    return {
        "query": query,
        "source": source,
        "items": items,
        "meta": {
            "total": resolved_total,
            "start": resolved_start,
            "display": resolved_display,
            "cached": cached,
        },
    }


def normalize_datalab_search_trends_response(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    return _normalize_datalab_response(payload, cached=False)


def normalize_datalab_search_trends_response_with_meta(
    payload: Mapping[str, Any],
    *,
    cached: bool = False,
) -> dict[str, Any]:
    return _normalize_datalab_response(payload, cached=cached)


def normalize_spell_check_response(
    query: str,
    payload: Mapping[str, Any],
    *,
    cached: bool = False,
) -> dict[str, Any]:
    corrected = _extract_single_value(payload, "errata")
    corrected_query = strip_html(corrected) or query
    return {
        "query": query,
        "corrected_query": corrected_query,
        "changed": corrected_query != query,
        "meta": {"cached": cached},
    }


def normalize_adult_query_response(
    query: str,
    payload: Mapping[str, Any],
    *,
    cached: bool = False,
) -> dict[str, Any]:
    adult_value = _extract_single_value(payload, "adult")
    normalized_flag = str(adult_value).strip().lower()
    is_adult = normalized_flag in {"1", "true", "y", "yes"}
    return {
        "query": query,
        "is_adult": is_adult,
        "meta": {"cached": cached},
    }


def normalize_datalab_category_trends_response(
    payload: Mapping[str, Any],
    *,
    cached: bool = False,
) -> dict[str, Any]:
    return _normalize_datalab_response(payload, cached=cached)


def normalize_datalab_device_trends_response(
    payload: Mapping[str, Any],
    *,
    cached: bool = False,
) -> dict[str, Any]:
    return _normalize_datalab_response(payload, cached=cached)


def _extract_single_value(payload: Mapping[str, Any], field_name: str) -> str:
    # errata/adult 응답은 배포 환경에 따라 필드 중첩 형태가 달라질 수 있어 여러 경로를 순차 탐색한다.
    direct = payload.get(field_name)
    if direct is not None:
        return str(direct)

    result = payload.get("result")
    if isinstance(result, Mapping):
        nested = result.get(field_name)
        if nested is not None:
            return str(nested)

        item = result.get("item")
        extracted = _extract_value_from_item_container(item, field_name)
        if extracted is not None:
            return extracted

    extracted = _extract_value_from_item_container(payload.get("item"), field_name)
    if extracted is not None:
        return extracted

    extracted = _extract_value_from_item_container(payload.get("items"), field_name)
    if extracted is not None:
        return extracted

    return ""


def _extract_value_from_item_container(item: Any, field_name: str) -> Optional[str]:
    if isinstance(item, Mapping):
        value = item.get(field_name)
        if value is not None:
            return str(value)
        return None
    if isinstance(item, Iterable) and not isinstance(item, (str, bytes, bytearray)):
        for candidate in item:
            if isinstance(candidate, Mapping) and candidate.get(field_name) is not None:
                return str(candidate.get(field_name))
    return None


def _normalize_datalab_response(
    payload: Mapping[str, Any],
    *,
    cached: bool,
) -> dict[str, Any]:
    # DataLab 계열은 결과 구조가 유사하므로 공통 normalizer에서 메타까지 함께 맞춘다.
    raw_results = payload.get("results", [])
    results: list[dict[str, Any]] = []
    for result in raw_results:
        if not isinstance(result, Mapping):
            continue
        data_points = []
        for point in result.get("data", []):
            if not isinstance(point, Mapping):
                continue
            ratio = point.get("ratio")
            try:
                ratio_value = float(ratio)
            except (TypeError, ValueError):
                ratio_value = 0.0
            normalized_point = {
                "period": str(point.get("period") or ""),
                "ratio": ratio_value,
            }
            group = point.get("group")
            # 기기 트렌드처럼 group이 있는 경우에만 보존한다.
            if group is not None and str(group).strip():
                normalized_point["group"] = str(group)
            data_points.append(normalized_point)

        normalized_result: dict[str, Any] = {
            "title": str(result.get("title") or ""),
            "data": data_points,
        }

        keywords = result.get("keywords")
        if isinstance(keywords, Iterable) and not isinstance(
            keywords, (str, bytes, bytearray)
        ):
            normalized_result["keywords"] = [
                str(keyword) for keyword in keywords if str(keyword).strip()
            ]
        elif result.get("keyword"):
            normalized_result["keywords"] = [str(result.get("keyword"))]

        category = result.get("category")
        if isinstance(category, Iterable) and not isinstance(
            category, (str, bytes, bytearray)
        ):
            normalized_result["category"] = [
                str(value) for value in category if str(value).strip()
            ]
        elif category is not None and str(category).strip():
            normalized_result["category"] = [str(category)]

        results.append(normalized_result)

    return {
        "results": results,
        "meta": {
            "start_date": str(payload.get("startDate") or ""),
            "end_date": str(payload.get("endDate") or ""),
            "time_unit": str(payload.get("timeUnit") or ""),
            "cached": cached,
        },
    }
