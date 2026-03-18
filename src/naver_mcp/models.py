from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable

from .errors import ValidationError

MAX_DISPLAY = 100
MAX_START = 1000
VALID_TIME_UNITS = {"date", "week", "month"}
VALID_DEVICE_FILTERS = {"", "pc", "mo"}
VALID_GENDERS = {"", "m", "f"}
VALID_AGES = {"10", "20", "30", "40", "50", "60"}
VALID_IMAGE_FILTERS = {"all", "large", "medium", "small"}
VALID_SHOP_SORTS = {"sim", "date", "asc", "dsc"}
VALID_SHOP_FILTERS = {"", "naverpay"}
VALID_SHOP_EXCLUDES = {"used", "rental", "cbshop"}


def _validate_non_empty(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValidationError(f"{field_name} must not be empty")
    return normalized


def _normalize_optional_str(value: str) -> str:
    return value.strip()


def _validate_query(query: str) -> str:
    return _validate_non_empty(query, "query")


def _validate_display(display: int) -> int:
    if not 1 <= display <= MAX_DISPLAY:
        raise ValidationError("display must be between 1 and 100")
    return display


def _validate_start(start: int) -> int:
    if not 1 <= start <= MAX_START:
        raise ValidationError("start must be between 1 and 1000")
    return start


def _validate_sort(sort: str, allowed: set[str]) -> str:
    normalized = sort.strip()
    if normalized not in allowed:
        allowed_text = ", ".join(sorted(allowed))
        raise ValidationError(f"sort must be one of: {allowed_text}")
    return normalized


def _validate_iso_date(value: str, field_name: str) -> str:
    normalized = _validate_non_empty(value, field_name)
    try:
        datetime.strptime(normalized, "%Y-%m-%d")
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be in YYYY-MM-DD format") from exc
    return normalized


def _validate_time_unit(time_unit: str) -> str:
    normalized = time_unit.strip()
    if normalized not in VALID_TIME_UNITS:
        raise ValidationError("time_unit must be one of: date, week, month")
    return normalized


def _validate_device(device: str) -> str:
    normalized = device.strip()
    if normalized not in VALID_DEVICE_FILTERS:
        raise ValidationError("device must be one of: '', pc, mo")
    return normalized


def _validate_gender(gender: str) -> str:
    normalized = gender.strip()
    if normalized not in VALID_GENDERS:
        raise ValidationError("gender must be one of: '', m, f")
    return normalized


def _validate_ages(ages: Iterable[object]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for age in ages:
        value = str(age).strip()
        if not value:
            continue
        if value not in VALID_AGES:
            raise ValidationError("ages must contain only: 10, 20, 30, 40, 50, 60")
        if value not in seen:
            normalized.append(value)
            seen.add(value)
    return normalized


def _normalize_str_list(values: Iterable[object], field_name: str) -> list[str]:
    normalized = [str(value).strip() for value in values if str(value).strip()]
    if not normalized:
        raise ValidationError(f"{field_name} must not be empty")
    return normalized


def _validate_shop_filter(value: str) -> str:
    normalized = value.strip()
    if normalized not in VALID_SHOP_FILTERS:
        raise ValidationError("filter must be one of: '', naverpay")
    return normalized


def _validate_shop_exclude(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        return ""
    options = [part.strip() for part in normalized.split(":") if part.strip()]
    if not options:
        return ""
    invalid = [option for option in options if option not in VALID_SHOP_EXCLUDES]
    if invalid:
        raise ValidationError("exclude must contain only: used, rental, cbshop")
    return ":".join(options)


@dataclass(frozen=True)
class BaseSearchRequest:
    query: str
    display: int = 5
    start: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "query", _validate_query(self.query))
        object.__setattr__(self, "display", _validate_display(self.display))
        object.__setattr__(self, "start", _validate_start(self.start))

    def to_params(self) -> dict[str, object]:
        return {
            "query": self.query,
            "display": self.display,
            "start": self.start,
        }


@dataclass(frozen=True)
class SortableSearchRequest(BaseSearchRequest):
    sort: str = "sim"
    allowed_sorts: tuple[str, ...] = field(default=("sim", "date"), init=False)

    def __post_init__(self) -> None:
        super().__post_init__()
        object.__setattr__(self, "sort", _validate_sort(self.sort, set(self.allowed_sorts)))

    def to_params(self) -> dict[str, object]:
        params = super().to_params()
        params["sort"] = self.sort
        return params


@dataclass(frozen=True)
class LocalSearchRequest(BaseSearchRequest):
    sort: str = "random"

    def __post_init__(self) -> None:
        super().__post_init__()
        object.__setattr__(self, "sort", _validate_sort(self.sort, {"random", "comment"}))

    def to_params(self) -> dict[str, object]:
        params = super().to_params()
        params["sort"] = self.sort
        return params


@dataclass(frozen=True)
class BlogSearchRequest(SortableSearchRequest):
    pass


@dataclass(frozen=True)
class WebSearchRequest(BaseSearchRequest):
    pass


@dataclass(frozen=True)
class NewsSearchRequest(SortableSearchRequest):
    pass


@dataclass(frozen=True)
class CafeArticleSearchRequest(SortableSearchRequest):
    pass


@dataclass(frozen=True)
class ImageSearchRequest(SortableSearchRequest):
    filter: str = "all"

    def __post_init__(self) -> None:
        super().__post_init__()
        normalized_filter = self.filter.strip()
        if normalized_filter not in VALID_IMAGE_FILTERS:
            raise ValidationError("filter must be one of: all, large, medium, small")
        object.__setattr__(self, "filter", normalized_filter)

    def to_params(self) -> dict[str, object]:
        params = super().to_params()
        params["filter"] = self.filter
        return params


@dataclass(frozen=True)
class BookSearchRequest(SortableSearchRequest):
    pass


@dataclass(frozen=True)
class EncycSearchRequest(BaseSearchRequest):
    pass


@dataclass(frozen=True)
class KinSearchRequest(SortableSearchRequest):
    sort: str = "sim"
    allowed_sorts: tuple[str, ...] = field(default=("sim", "date", "point"), init=False)


@dataclass(frozen=True)
class ShopSearchRequest(SortableSearchRequest):
    sort: str = "sim"
    allowed_sorts: tuple[str, ...] = field(default=("asc", "date", "dsc", "sim"), init=False)
    filter: str = ""
    exclude: str = ""

    def __post_init__(self) -> None:
        super().__post_init__()
        object.__setattr__(self, "filter", _validate_shop_filter(self.filter))
        object.__setattr__(self, "exclude", _validate_shop_exclude(self.exclude))

    def to_params(self) -> dict[str, object]:
        params = super().to_params()
        if self.filter:
            params["filter"] = self.filter
        if self.exclude:
            params["exclude"] = self.exclude
        return params


@dataclass(frozen=True)
class DocSearchRequest(BaseSearchRequest):
    pass


@dataclass(frozen=True)
class BookAdvancedSearchRequest:
    query: str = ""
    display: int = 5
    start: int = 1
    sort: str = "sim"
    title: str = ""
    isbn: str = ""

    def __post_init__(self) -> None:
        normalized_query = _normalize_optional_str(self.query)
        normalized_title = _normalize_optional_str(self.title)
        normalized_isbn = _normalize_optional_str(self.isbn)
        if not normalized_title and not normalized_isbn:
            raise ValidationError("title or isbn must be provided for advanced book search")

        object.__setattr__(self, "query", normalized_query or normalized_title or normalized_isbn)
        object.__setattr__(self, "title", normalized_title)
        object.__setattr__(self, "isbn", normalized_isbn)
        object.__setattr__(self, "display", _validate_display(self.display))
        object.__setattr__(self, "start", _validate_start(self.start))
        object.__setattr__(self, "sort", _validate_sort(self.sort, {"sim", "date"}))

    def to_params(self) -> dict[str, object]:
        params: dict[str, object] = {
            "display": self.display,
            "start": self.start,
            "sort": self.sort,
        }
        if self.query:
            params["query"] = self.query
        if self.title:
            params["d_titl"] = self.title
        if self.isbn:
            params["d_isbn"] = self.isbn
        return params


@dataclass(frozen=True)
class QueryOnlyRequest:
    query: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "query", _validate_query(self.query))

    def to_params(self) -> dict[str, object]:
        return {"query": self.query}


@dataclass(frozen=True)
class DataLabKeywordGroup:
    group_name: str
    keywords: list[str]

    def __post_init__(self) -> None:
        name = _validate_non_empty(self.group_name, "group_name")
        normalized_keywords = _normalize_str_list(self.keywords, "keywords")
        object.__setattr__(self, "group_name", name)
        object.__setattr__(self, "keywords", normalized_keywords)

    def to_payload(self) -> dict[str, object]:
        return {"groupName": self.group_name, "keywords": self.keywords}


@dataclass(frozen=True)
class DataLabSearchTrendsRequest:
    start_date: str
    end_date: str
    time_unit: str
    keyword_groups: list[DataLabKeywordGroup]

    def __post_init__(self) -> None:
        object.__setattr__(self, "start_date", _validate_iso_date(self.start_date, "start_date"))
        object.__setattr__(self, "end_date", _validate_iso_date(self.end_date, "end_date"))
        object.__setattr__(self, "time_unit", _validate_time_unit(self.time_unit))
        if not self.keyword_groups:
            raise ValidationError("keyword_groups must not be empty")

    def to_payload(self) -> dict[str, object]:
        return {
            "startDate": self.start_date,
            "endDate": self.end_date,
            "timeUnit": self.time_unit,
            "keywordGroups": [group.to_payload() for group in self.keyword_groups],
        }


@dataclass(frozen=True)
class DataLabCategoryGroup:
    name: str
    params: list[str]

    def __post_init__(self) -> None:
        normalized_name = _validate_non_empty(self.name, "name")
        normalized_params = _normalize_str_list(self.params, "params")
        object.__setattr__(self, "name", normalized_name)
        object.__setattr__(self, "params", normalized_params)

    def to_payload(self) -> dict[str, object]:
        return {"name": self.name, "param": self.params}


@dataclass(frozen=True)
class DataLabShoppingKeywordGroup:
    name: str
    params: list[str]

    def __post_init__(self) -> None:
        normalized_name = _validate_non_empty(self.name, "name")
        normalized_params = _normalize_str_list(self.params, "params")
        if len(normalized_params) != 1:
            raise ValidationError("keyword params must contain exactly one keyword")
        object.__setattr__(self, "name", normalized_name)
        object.__setattr__(self, "params", normalized_params)

    def to_payload(self) -> dict[str, object]:
        return {"name": self.name, "param": self.params}


@dataclass(frozen=True)
class DataLabShoppingCategoryTrendsRequest:
    start_date: str
    end_date: str
    time_unit: str
    categories: list[DataLabCategoryGroup]
    device: str = ""
    gender: str = ""
    ages: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "start_date", _validate_iso_date(self.start_date, "start_date"))
        object.__setattr__(self, "end_date", _validate_iso_date(self.end_date, "end_date"))
        object.__setattr__(self, "time_unit", _validate_time_unit(self.time_unit))
        if not self.categories:
            raise ValidationError("categories must not be empty")
        if len(self.categories) > 3:
            raise ValidationError("categories must contain at most 3 groups")
        object.__setattr__(self, "device", _validate_device(self.device))
        object.__setattr__(self, "gender", _validate_gender(self.gender))
        object.__setattr__(self, "ages", _validate_ages(self.ages))

    def to_payload(self) -> dict[str, object]:
        return {
            "startDate": self.start_date,
            "endDate": self.end_date,
            "timeUnit": self.time_unit,
            "category": [category.to_payload() for category in self.categories],
            "device": self.device,
            "gender": self.gender,
            "ages": self.ages,
        }


@dataclass(frozen=True)
class DataLabShoppingCategoryDetailRequest:
    start_date: str
    end_date: str
    time_unit: str
    category: str
    device: str = ""
    gender: str = ""
    ages: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "start_date", _validate_iso_date(self.start_date, "start_date"))
        object.__setattr__(self, "end_date", _validate_iso_date(self.end_date, "end_date"))
        object.__setattr__(self, "time_unit", _validate_time_unit(self.time_unit))
        object.__setattr__(self, "category", _validate_non_empty(self.category, "category"))
        object.__setattr__(self, "device", _validate_device(self.device))
        object.__setattr__(self, "gender", _validate_gender(self.gender))
        object.__setattr__(self, "ages", _validate_ages(self.ages))

    def to_payload(self) -> dict[str, object]:
        return {
            "startDate": self.start_date,
            "endDate": self.end_date,
            "timeUnit": self.time_unit,
            "category": self.category,
            "device": self.device,
            "gender": self.gender,
            "ages": self.ages,
        }


@dataclass(frozen=True)
class DataLabShoppingKeywordTrendsRequest:
    start_date: str
    end_date: str
    time_unit: str
    category: str
    keywords: list[DataLabShoppingKeywordGroup]
    device: str = ""
    gender: str = ""
    ages: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "start_date", _validate_iso_date(self.start_date, "start_date"))
        object.__setattr__(self, "end_date", _validate_iso_date(self.end_date, "end_date"))
        object.__setattr__(self, "time_unit", _validate_time_unit(self.time_unit))
        object.__setattr__(self, "category", _validate_non_empty(self.category, "category"))
        if not self.keywords:
            raise ValidationError("keywords must not be empty")
        if len(self.keywords) > 5:
            raise ValidationError("keywords must contain at most 5 groups")
        object.__setattr__(self, "device", _validate_device(self.device))
        object.__setattr__(self, "gender", _validate_gender(self.gender))
        object.__setattr__(self, "ages", _validate_ages(self.ages))

    def to_payload(self) -> dict[str, object]:
        return {
            "startDate": self.start_date,
            "endDate": self.end_date,
            "timeUnit": self.time_unit,
            "category": self.category,
            "keyword": [keyword.to_payload() for keyword in self.keywords],
            "device": self.device,
            "gender": self.gender,
            "ages": self.ages,
        }


@dataclass(frozen=True)
class DataLabShoppingKeywordDetailRequest:
    start_date: str
    end_date: str
    time_unit: str
    category: str
    keyword: str
    device: str = ""
    gender: str = ""
    ages: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(self, "start_date", _validate_iso_date(self.start_date, "start_date"))
        object.__setattr__(self, "end_date", _validate_iso_date(self.end_date, "end_date"))
        object.__setattr__(self, "time_unit", _validate_time_unit(self.time_unit))
        object.__setattr__(self, "category", _validate_non_empty(self.category, "category"))
        object.__setattr__(self, "keyword", _validate_non_empty(self.keyword, "keyword"))
        object.__setattr__(self, "device", _validate_device(self.device))
        object.__setattr__(self, "gender", _validate_gender(self.gender))
        object.__setattr__(self, "ages", _validate_ages(self.ages))

    def to_payload(self) -> dict[str, object]:
        return {
            "startDate": self.start_date,
            "endDate": self.end_date,
            "timeUnit": self.time_unit,
            "category": self.category,
            "keyword": self.keyword,
            "device": self.device,
            "gender": self.gender,
            "ages": self.ages,
        }
