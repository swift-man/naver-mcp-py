# Tool Contract

## Purpose

This document defines the public MCP contract for `naver-mcp-py`.

The contract is intended to stay stable for external consumers such as:

- chat applications
- orchestration layers
- integration tests
- wrapper services

## Transport

Primary transport:

- MCP over `streamable-http`

Example endpoint:

- `http://127.0.0.1:8100/mcp`

The actual path may change through `NAVER_MCP_PATH`. Clients must use the exact configured path.

Upstream NAVER API HUB calls use:

```text
Base URL: https://naverapihub.apigw.ntruss.com
Client ID: X-NCP-APIGW-API-KEY-ID
Client Secret: X-NCP-APIGW-API-KEY
```

`NAVER_API_BASE_URL` must use HTTPS. Plain HTTP is accepted only for an explicit
loopback host such as `localhost`, `127.0.0.1`, or `::1` during local testing.

## Common Search Response Shape

Search tools return this shape whenever practical:

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
  "source": "local|blog|web|news|cafearticle|image|encyc|kin",
  "published_at": "2026-03-18T12:00:00+09:00",
  "score": 0.0
}
```

Notes:

- HTML tags are stripped from user-facing text fields
- `published_at` is normalized when the source provides a parsable date
- `score` is deterministic tool-side metadata, not a raw Naver score

## Source-Specific Search Fields

### Local

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

### Blog, News, Web, Cafe, Kin

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

Only fields present in the source response are included.

### Image

```json
{
  "thumbnail": "https://...",
  "size_height": "480",
  "size_width": "640"
}
```

### Encyclopedia

```json
{
  "thumbnail": "https://...",
  "description": "encyclopedia summary"
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

- `sort` supports `random` and `comment`
- `display` supports `1` through `5`
- `start` must be `1`

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

- `sort` supports `sim` and `date`

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

### `search_image`

Input:

```json
{
  "query": "cats",
  "display": 5,
  "start": 1,
  "sort": "sim",
  "filter": "large"
}
```

Notes:

- `sort` supports `sim` and `date`
- `filter` supports `all`, `large`, `medium`, `small`

### `search_book`

Compatibility-only tool. Always raises `NAVER_SERVICE_UNAVAILABLE` without making a network request.

### `search_book_advanced`

Compatibility-only tool. Always raises `NAVER_SERVICE_UNAVAILABLE` without making a network request.

### `search_encyc`

Input:

```json
{
  "query": "black hole",
  "display": 5,
  "start": 1
}
```

### `search_kin`

Input:

```json
{
  "query": "how to install python",
  "display": 5,
  "start": 1,
  "sort": "point"
}
```

Notes:

- `sort` supports `sim`, `date`, and `point`

### `search_shop`

Compatibility-only tool. Always raises `NAVER_SERVICE_UNAVAILABLE` without making a network request.

### `search_doc`

Compatibility-only tool. Always raises `NAVER_SERVICE_UNAVAILABLE` without making a network request.

Naver ended book, shopping product, and professional document search on 2026-07-31 and did not provide replacement NAVER API HUB endpoints.

### `spell_check`

Input:

```json
{
  "query": "pangyp restaurants"
}
```

Output:

```json
{
  "query": "pangyp restaurants",
  "corrected_query": "pangyo restaurants",
  "changed": true,
  "meta": {
    "cached": false
  }
}
```

The upstream `errata` value must be a string. An empty string is valid and means
that NAVER found no typo.

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

The upstream `adult` field must be the documented string code `"0"` or `"1"`.
Missing or unknown values are returned as `NAVER_API_ERROR` instead of being
treated as a non-adult result.

### `search_naver_auto`

Purpose:

Provide a convenience router for obvious intents while disclosing which low-level sources were used.

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
    "deduplicated": 0,
    "fallback": false,
    "cached": false
  }
}
```

`meta.fallback_reason` is present only when `meta.fallback` is `true`. Its
currently supported value is `source_api_retired` for book and shopping routes
that use fallback sources because the original source API was retired.

```json
{
  "fallback": true,
  "fallback_reason": "source_api_retired"
}
```

Requirements:

- the selected intent must be disclosed
- the list of sources must be disclosed
- ranking and merge rules must be documented

Current merge policy:

- `place_search` -> `local` then `blog`
- `news_search` -> `news`
- `book_search` -> `web` then `blog`, with `meta.fallback: true`
- `shopping_search` -> `web` then `blog`, with `meta.fallback: true`
- `community_search` -> `blog` then `cafearticle`
- `general_web` -> `web` then `blog`
- duplicate items are removed using `originallink`, then `link`, then `source:title`
- `score` is assigned deterministically from source priority and within-source rank

## DataLab Tools

### Common DataLab Response Shape

```json
{
  "results": [
    {
      "title": "fashion",
      "category": ["50000000"],
      "keywords": ["러닝화"],
      "data": [
        {
          "period": "2026-03-01",
          "ratio": 51.2,
          "group": "pc"
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

- `category` appears for shopping category and shopping keyword tools
- `keywords` appears for search trends and shopping keyword tools
- `group` appears only for breakdown tools such as device, gender, or age
- `ratio` is a finite number from `0` through `100`

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
  ],
  "device": "pc",
  "gender": "f",
  "ages": ["3", "4"]
}
```

Notes:

- `keyword_groups` accepts up to 5 groups
- each group accepts up to 20 keywords
- Search Trend age codes are `1` through `11`
- empty optional filters are omitted from the upstream request

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

Notes:

- `categories` accepts up to 3 groups
- each category group maps to Naver `category[].param`

### `datalab_shopping_category_device_trends`

Input:

```json
{
  "start_date": "2026-03-01",
  "end_date": "2026-03-18",
  "time_unit": "date",
  "category": "50000000",
  "device": "",
  "gender": "f",
  "ages": ["20", "30"]
}
```

Notes:

- `data[].group` contains the device bucket such as `pc` or `mo`

### `datalab_shopping_category_gender_trends`

Input:

```json
{
  "start_date": "2026-03-01",
  "end_date": "2026-03-18",
  "time_unit": "date",
  "category": "50000000",
  "device": "mo"
}
```

Notes:

- `data[].group` contains the gender bucket such as `f` or `m`

### `datalab_shopping_category_age_trends`

Input:

```json
{
  "start_date": "2026-03-01",
  "end_date": "2026-03-18",
  "time_unit": "date",
  "category": "50000000",
  "gender": "f"
}
```

Notes:

- `data[].group` contains the age bucket such as `20` or `30`

### `datalab_shopping_keyword_trends`

Input:

```json
{
  "start_date": "2026-03-01",
  "end_date": "2026-03-18",
  "time_unit": "week",
  "category": "50000000",
  "keywords": [
    {
      "name": "running shoes",
      "params": ["running shoes"]
    }
  ],
  "device": "pc"
}
```

Notes:

- `keywords` accepts up to 5 groups
- each keyword group must contain exactly 1 keyword inside `params`

### `datalab_shopping_keyword_device_trends`

Input:

```json
{
  "start_date": "2026-03-01",
  "end_date": "2026-03-18",
  "time_unit": "date",
  "category": "50000000",
  "keyword": "running shoes"
}
```

Notes:

- `data[].group` contains the device bucket

### `datalab_shopping_keyword_gender_trends`

Input:

```json
{
  "start_date": "2026-03-01",
  "end_date": "2026-03-18",
  "time_unit": "date",
  "category": "50000000",
  "keyword": "running shoes"
}
```

Notes:

- `data[].group` contains the gender bucket

### `datalab_shopping_keyword_age_trends`

Input:

```json
{
  "start_date": "2026-03-01",
  "end_date": "2026-03-18",
  "time_unit": "date",
  "category": "50000000",
  "keyword": "running shoes"
}
```

Notes:

- `data[].group` contains the age bucket

### `datalab_shopping_device_trends`

Purpose:

Backward-compatible alias of `datalab_shopping_category_device_trends`.

Input:

```json
{
  "start_date": "2026-03-01",
  "end_date": "2026-03-18",
  "time_unit": "date",
  "category": "50000000"
}
```

## Validation Rules

- `query` must not be empty for search tools unless the tool explicitly allows an empty `query` field
- `display` must be between `1` and `100`
- `start` must be between `1` and `1000`
- `search_local.display` must be between `1` and `5`
- `search_local.start` must be `1`
- `search_image.filter` must be one of `all`, `large`, `medium`, `small`
- `start_date` and `end_date` must be valid `YYYY-MM-DD`, and `start_date` must not be later than `end_date`
- `time_unit` must be one of `date`, `week`, `month`
- `keyword_groups` must contain 1 through 5 groups for `datalab_search_trends`
- Search Trend `ages` must contain only codes `1` through `11`
- shopping `categories` must be non-empty and limited to 3 groups
- shopping keyword groups must be non-empty and limited to 5 groups
- each shopping keyword trend group must contain exactly 1 keyword in `params`
- `device` must be one of `""`, `pc`, `mo`
- `gender` must be one of `""`, `m`, `f`
- `ages` must contain only `10`, `20`, `30`, `40`, `50`, `60`
- NAVER API HUB documents `device`, `gender`, and `ages` as optional filters on all six category and keyword breakdown endpoints; supplied filters are forwarded unchanged
- `ages`, group `keywords`, and group `params` must be JSON arrays of strings, not scalar strings
- `keyword_groups`, `categories`, and shopping `keywords` must contain only their documented group object shapes

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
- `NAVER_SERVICE_UNAVAILABLE`
- `VALIDATION_ERROR`

`NAVER_RATE_LIMIT` represents the API HUB daily quota response and returns
`retryable: false`. `NAVER_TIMEOUT` and temporary 5xx `NAVER_API_ERROR`
responses may return `retryable: true`.

## Timeout Guidance

Suggested defaults:

- search tools: 6 to 8 seconds
- DataLab tools: 8 to 10 seconds

## Cache Guidance

Suggested defaults:

- search tools: 5 minutes
- spell check and adult detection: 30 minutes
- DataLab tools: 30 minutes or longer

## Backward Compatibility

- additive fields are allowed
- field renames should be avoided
- tool names should be treated as stable once published
- `datalab_shopping_device_trends` is retained as an alias for existing clients
- retired search tool names are retained and return `NAVER_SERVICE_UNAVAILABLE`
- major contract changes should be documented before implementation
