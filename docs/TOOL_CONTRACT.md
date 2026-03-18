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
  "source": "local|blog|web|news|cafearticle|image|book|encyc|kin|shop|doc",
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

### Blog, News, Web, Cafe, Kin, Doc

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

### Book

```json
{
  "image": "https://...",
  "author": "author name",
  "discount": "18000",
  "publisher": "publisher name",
  "isbn": "9781234567890",
  "description": "book summary"
}
```

### Encyclopedia

```json
{
  "thumbnail": "https://...",
  "description": "encyclopedia summary"
}
```

### Shop

```json
{
  "image": "https://...",
  "low_price": "99000",
  "high_price": "159000",
  "mall_name": "mall",
  "product_id": "123456",
  "product_type": "2",
  "brand": "brand",
  "maker": "maker",
  "category1": "디지털/가전",
  "category2": "음향가전",
  "category3": "이어폰",
  "category4": ""
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

Input:

```json
{
  "query": "python",
  "display": 5,
  "start": 1,
  "sort": "sim"
}
```

Notes:

- `sort` supports `sim` and `date`

### `search_book_advanced`

Purpose:

Wrap Naver advanced book lookup while keeping the same normalized `source: "book"` response shape.

Input:

```json
{
  "query": "",
  "display": 5,
  "start": 1,
  "sort": "sim",
  "title": "clean code",
  "isbn": ""
}
```

Notes:

- at least one of `title` or `isbn` is required
- if `query` is omitted, the tool uses `title` or `isbn` as the normalized query
- `sort` supports `sim` and `date`

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

Input:

```json
{
  "query": "wireless earbuds",
  "display": 5,
  "start": 1,
  "sort": "sim",
  "filter": "naverpay",
  "exclude": "used:cbshop"
}
```

Notes:

- `sort` supports `sim`, `date`, `asc`, `dsc`
- `filter` supports `""` and `naverpay`
- `exclude` is a colon-separated list of `used`, `rental`, `cbshop`

### `search_doc`

Input:

```json
{
  "query": "generative ai report",
  "display": 5,
  "start": 1
}
```

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
    "cached": false
  }
}
```

Requirements:

- the selected intent must be disclosed
- the list of sources must be disclosed
- ranking and merge rules must be documented

Current merge policy:

- `place_search` -> `local` then `blog`
- `news_search` -> `news`
- `book_search` -> `book`
- `shopping_search` -> `shop` then `blog`
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
- `search_image.filter` must be one of `all`, `large`, `medium`, `small`
- `search_shop.filter` must be `""` or `naverpay`
- `search_shop.exclude` must contain only `used`, `rental`, `cbshop`
- `search_book_advanced` requires `title` or `isbn`
- `start_date` and `end_date` must be valid `YYYY-MM-DD`
- `time_unit` must be one of `date`, `week`, `month`
- `keyword_groups` must be non-empty for `datalab_search_trends`
- shopping `categories` must be non-empty and limited to 3 groups
- shopping keyword groups must be non-empty and limited to 5 groups
- each shopping keyword trend group must contain exactly 1 keyword in `params`
- `device` must be one of `""`, `pc`, `mo`
- `gender` must be one of `""`, `m`, `f`
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
- spell check and adult detection: 30 minutes
- DataLab tools: 30 minutes or longer

## Backward Compatibility

- additive fields are allowed
- field renames should be avoided
- tool names should be treated as stable once published
- `datalab_shopping_device_trends` is retained as an alias for existing clients
- major contract changes should be documented before implementation
