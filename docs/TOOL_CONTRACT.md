# Tool Contract

## Purpose

This document defines the public contract for `naver-mcp-py`.

The contract should be stable enough for external clients such as:

- chat applications
- orchestration layers
- test harnesses

## Transport

Primary transport:

- MCP over `streamable-http`

Example endpoint:

- MCP: `http://127.0.0.1:8100/mcp`

Health checks may be exposed by the embedding HTTP app or process manager when needed.

## Common Response Shape

Search tools should return this shape whenever practical:

```json
{
  "query": "pangyo restaurants",
  "source": "local",
  "items": [],
  "meta": {
    "total": 123,
    "start": 1,
    "display": 5,
    "cached": false
  }
}
```

## Common Search Item Shape

```json
{
  "title": "normalized title",
  "link": "https://...",
  "snippet": "normalized snippet",
  "source": "local|blog|web|news|cafearticle",
  "published_at": "2026-03-18T12:00:00+09:00",
  "score": 0.0
}
```

Optional source-specific fields may be appended.

## Source-Specific Extensions

### Local Search Fields

```json
{
  "name": "restaurant name",
  "category": "Korean",
  "address": "Seongnam-si ...",
  "road_address": "Bundang-gu ...",
  "telephone": "031-000-0000",
  "mapx": "127...",
  "mapy": "37..."
}
```

### Blog, News, Web, Cafe Fields

```json
{
  "originallink": "https://...",
  "blogger_name": "author",
  "blogger_link": "https://...",
  "cafe_name": "community name",
  "cafe_url": "https://cafe.naver.com/...",
  "description": "original description"
}
```

## Search Tools

### `search_local`

Input:

```json
{
  "query": "pangyo restaurants",
  "display": 5,
  "start": 1,
  "sort": "comment"
}
```

Notes:

- `sort` follows Naver local search semantics
- the server validates `display` and `start`

### `search_blog`

Input:

```json
{
  "query": "kimchi jjigae recipe",
  "display": 5,
  "start": 1,
  "sort": "sim"
}
```

Notes:

- HTML tags are removed from `title` and `snippet`

### `search_web`

Input:

```json
{
  "query": "kimchi jjigae recipe",
  "display": 5,
  "start": 1
}
```

### `search_news`

Input:

```json
{
  "query": "pangyo startup news",
  "display": 5,
  "start": 1,
  "sort": "date"
}
```

Notes:

- `sort` supports `sim` and `date`

### `search_cafearticle`

Input:

```json
{
  "query": "pangyo restaurant reviews",
  "display": 5,
  "start": 1,
  "sort": "sim"
}
```

Notes:

- `sort` supports `sim` and `date`
- `cafe_name` and `cafe_url` are returned when present

### `spell_check`

Input:

```json
{
  "query": "pangyo restaurants"
}
```

Output:

```json
{
  "query": "pangyo restaurants",
  "corrected_query": "pangyo restaurants",
  "changed": false,
  "meta": {
    "cached": false
  }
}
```

### `detect_adult_query`

Input:

```json
{
  "query": "search text"
}
```

Output:

```json
{
  "query": "search text",
  "is_adult": false,
  "meta": {
    "cached": false
  }
}
```

### `search_naver_auto`

Purpose:

Provide a convenience routing tool for obvious search intents.

Input:

```json
{
  "query": "pangyo restaurants",
  "display": 5
}
```

Output:

```json
{
  "query": "pangyo restaurants",
  "intent": "place_search",
  "sources": ["local", "blog"],
  "items": [],
  "meta": {
    "display": 5,
    "cached": false
  }
}
```

Requirements:

- must disclose the selected intent
- must disclose the list of sources used
- must keep ranking and merge logic documented

Current merge policy:

- `place_search` -> `local` then `blog`
- `news_search` -> `news`
- `community_search` -> `blog` then `cafearticle`
- `general_web` -> `web` then `blog`
- results are merged in source priority order
- duplicate items are removed using `originallink`, then `link`, then `source:title`
- `score` is assigned deterministically from source priority and within-source rank

## DataLab Tools

### `datalab_search_trends`

Input:

```json
{
  "start_date": "2026-03-01",
  "end_date": "2026-03-18",
  "time_unit": "date",
  "keyword_groups": [
    {
      "group_name": "pangyo",
      "keywords": ["pangyo restaurants", "pangyo cafe"]
    }
  ]
}
```

Output:

```json
{
  "results": [
    {
      "title": "pangyo",
      "keywords": ["pangyo restaurants", "pangyo cafe"],
      "data": [
        {
          "period": "2026-03-01",
          "ratio": 78.1
        }
      ]
    }
  ],
  "meta": {
    "start_date": "2026-03-01",
    "end_date": "2026-03-18",
    "time_unit": "date",
    "cached": false
  }
}
```

### `datalab_shopping_category_trends`

Input:

```json
{
  "start_date": "2026-03-01",
  "end_date": "2026-03-18",
  "time_unit": "week",
  "categories": [
    {
      "name": "fashion",
      "params": ["50000000"]
    }
  ],
  "device": "pc",
  "gender": "f",
  "ages": ["20", "30"]
}
```

Output:

```json
{
  "results": [
    {
      "title": "fashion",
      "category": ["50000000"],
      "data": [
        {
          "period": "2026-03-01",
          "ratio": 51.2
        }
      ]
    }
  ],
  "meta": {
    "start_date": "2026-03-01",
    "end_date": "2026-03-18",
    "time_unit": "week",
    "cached": false
  }
}
```

Notes:

- `categories` accepts up to 3 groups
- each category group maps to Naver's `category[].param`

### `datalab_shopping_device_trends`

Input:

```json
{
  "start_date": "2026-03-01",
  "end_date": "2026-03-18",
  "time_unit": "date",
  "category": "50000000",
  "gender": "f",
  "ages": ["20", "30"]
}
```

Output:

```json
{
  "results": [
    {
      "title": "50000000",
      "category": ["50000000"],
      "data": [
        {
          "period": "2026-03-01",
          "group": "mo",
          "ratio": 81.1
        },
        {
          "period": "2026-03-01",
          "group": "pc",
          "ratio": 18.9
        }
      ]
    }
  ],
  "meta": {
    "start_date": "2026-03-01",
    "end_date": "2026-03-18",
    "time_unit": "date",
    "cached": false
  }
}
```

Notes:

- `group` represents the device bucket such as `pc` or `mo`
- optional `device`, `gender`, and `ages` filters are passed through to Naver DataLab

## Validation Rules

- `query` must not be empty for search tools
- `display` should be clamped or rejected outside supported ranges
- `start_date` and `end_date` must be valid ISO dates where applicable
- `keyword_groups` must be non-empty for DataLab trend tools
- shopping `categories` must be non-empty and limited to 3 groups
- `device` must be one of `pc`, `mo`, or empty
- `gender` must be one of `m`, `f`, or empty
- `ages` must contain only `10`, `20`, `30`, `40`, `50`, `60`

## Error Shape

Errors are structured as:

```json
{
  "error": {
    "code": "NAVER_API_ERROR",
    "message": "Naver API request failed",
    "retryable": true
  }
}
```

Recommended codes:

- `NAVER_AUTH_ERROR`
- `NAVER_RATE_LIMIT`
- `NAVER_TIMEOUT`
- `NAVER_API_ERROR`
- `VALIDATION_ERROR`

## Timeout Guidance

Suggested defaults:

- search tools: 6 to 8 seconds
- DataLab tools: 8 to 10 seconds

## Cache Guidance

Suggested defaults:

- search tools: 5 minutes
- spell and adult detection: 30 minutes
- DataLab tools: 30 minutes or longer

## Backward Compatibility

- additive fields are allowed
- field renames should be avoided
- tool names should be treated as stable once published
- major contract changes should be documented before implementation
