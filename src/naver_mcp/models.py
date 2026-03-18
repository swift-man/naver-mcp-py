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


def _validate_query(query: str) -> str:
    normalized = query.strip()
    if not normalized:
        raise ValidationError("query must not be empty")
    return normalized


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
    normalized = value.strip()
    if not normalized:
        raise ValidationError(f"{field_name} must not be empty")
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
class BlogSearchRequest(BaseSearchRequest):
    sort: str = "sim"

    def __post_init__(self) -> None:
        super().__post_init__()
        object.__setattr__(self, "sort", _validate_sort(self.sort, {"sim", "date"}))

    def to_params(self) -> dict[str, object]:
        params = super().to_params()
        params["sort"] = self.sort
        return params


@dataclass(frozen=True)
class WebSearchRequest(BaseSearchRequest):
    pass


@dataclass(frozen=True)
class NewsSearchRequest(BaseSearchRequest):
    sort: str = "sim"

    def __post_init__(self) -> None:
        super().__post_init__()
        object.__setattr__(self, "sort", _validate_sort(self.sort, {"sim", "date"}))

    def to_params(self) -> dict[str, object]:
        params = super().to_params()
        params["sort"] = self.sort
        return params


@dataclass(frozen=True)
class CafeArticleSearchRequest(BaseSearchRequest):
    sort: str = "sim"

    def __post_init__(self) -> None:
        super().__post_init__()
        object.__setattr__(self, "sort", _validate_sort(self.sort, {"sim", "date"}))

    def to_params(self) -> dict[str, object]:
        params = super().to_params()
        params["sort"] = self.sort
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
        name = self.group_name.strip()
        if not name:
            raise ValidationError("group_name must not be empty")
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
        object.__setattr__(
            self,
            "start_date",
            _validate_iso_date(self.start_date, "start_date"),
        )
        object.__setattr__(
            self,
            "end_date",
            _validate_iso_date(self.end_date, "end_date"),
        )
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
        normalized_name = self.name.strip()
        if not normalized_name:
            raise ValidationError("name must not be empty")
        normalized_params = _normalize_str_list(self.params, "params")
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
        object.__setattr__(
            self,
            "start_date",
            _validate_iso_date(self.start_date, "start_date"),
        )
        object.__setattr__(
            self,
            "end_date",
            _validate_iso_date(self.end_date, "end_date"),
        )
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
class DataLabShoppingDeviceTrendsRequest:
    start_date: str
    end_date: str
    time_unit: str
    category: str
    device: str = ""
    gender: str = ""
    ages: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "start_date",
            _validate_iso_date(self.start_date, "start_date"),
        )
        object.__setattr__(
            self,
            "end_date",
            _validate_iso_date(self.end_date, "end_date"),
        )
        object.__setattr__(self, "time_unit", _validate_time_unit(self.time_unit))
        normalized_category = self.category.strip()
        if not normalized_category:
            raise ValidationError("category must not be empty")
        object.__setattr__(self, "category", normalized_category)
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
