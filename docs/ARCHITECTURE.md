# Architecture

## Overview

`naver-mcp-py` is a dedicated Python repository that exposes NAVER API HUB Search, Search Trend, and Shopping Insight APIs as MCP tools.

The repository supports two modes:

- library mode: imported directly by another Python app
- server mode: exposed as a FastMCP server over `streamable-http`

## Why This Repository Exists

The main chat application should not own:

- Naver API authentication
- source-specific normalization
- search-specific caching and retries
- DataLab request shaping

By isolating those concerns here, chat applications can focus on routing and reply rendering.

## System Context

Typical deployment:

```mermaid
flowchart LR
    A["Chat App"] --> B["App Router or Orchestrator"]
    B --> C["naver-mcp-py"]
    B --> D["other MCP servers"]
    C --> E["NAVER API HUB"]
    E --> F["Search"]
    E --> G["Search Trend"]
    E --> H["Shopping Insight"]
```

## Repository Responsibilities

- authenticate against Naver APIs
- expose stable MCP tool surfaces
- normalize heterogeneous API responses into shared shapes
- handle timeout, retry, and cache policies
- provide a reusable server entry point for MCP deployment

## Non-Goals

- final end-user message phrasing
- persona or prompt logic
- room or channel policy
- multi-step planning across different domains

## Internal Layers

```text
server.py
  -> tools_search.py / tools_datalab.py
    -> client.py
    -> normalize.py
    -> models.py
    -> cache.py
```

### `config.py`

Holds environment parsing and defaults:

- API credentials
- validated upstream API base URL with HTTPS required outside loopback
- host and port
- MCP transport configuration
- remote-access protection mode
- JWT verifier configuration for authenticated remote access
- timeout and cache settings

### `client.py`

Owns raw HTTP calls to Naver APIs.

Responsibilities:

- build `X-NCP-APIGW-API-KEY-ID` and `X-NCP-APIGW-API-KEY` headers
- map tool calls to `/search/v1`, `/search-trend/v1`, and `/shopping/v1` endpoints
- send HTTP requests
- handle status codes
- map transport failures into structured exceptions

### `normalize.py`

Transforms raw Naver payloads into a stable contract.

Responsibilities:

- strip HTML tags
- normalize timestamps
- build common item fields
- preserve useful source-specific fields
- de-duplicate combined results for composite tools when needed

### `tools_search.py`

Exposes search-related MCP tools.

Implemented tools:

- `search_local`
- `search_blog`
- `search_web`
- `search_news`
- `search_cafearticle`
- `search_image`
- `search_encyc`
- `search_kin`
- `spell_check`
- `detect_adult_query`
- `search_naver_auto`

Compatibility-only retired tools:

- `search_book`
- `search_book_advanced`
- `search_shop`
- `search_doc`

The retired tools raise `NAVER_SERVICE_UNAVAILABLE` without a network request because Naver ended the underlying APIs on 2026-07-31.

### `tools_datalab.py`

Exposes trend-related MCP tools.

Implemented tools:

- `datalab_search_trends`
- `datalab_shopping_category_trends`
- `datalab_shopping_category_device_trends`
- `datalab_shopping_category_gender_trends`
- `datalab_shopping_category_age_trends`
- `datalab_shopping_keyword_trends`
- `datalab_shopping_keyword_device_trends`
- `datalab_shopping_keyword_gender_trends`
- `datalab_shopping_keyword_age_trends`
- `datalab_shopping_device_trends`

### `server.py`

Defines:

- FastMCP server object
- MCP tool registration
- a common boundary that converts `NaverMCPError` exceptions into structured tool responses
- main process entry point
- a lightweight `healthz()` helper for embedding scenarios

## Design Decisions

### Common Response Contract

Whenever practical, search tools return:

```json
{
  "query": "example query",
  "source": "local",
  "items": [],
  "meta": {
    "total": 0,
    "start": 1,
    "display": 5,
    "cached": false
  }
}
```

This keeps clients simple and makes composite tools easier to build.

### Common Item Contract

All search tools try to emit:

```json
{
  "title": "normalized title",
  "link": "https://...",
  "snippet": "normalized description",
  "source": "local|blog|web|news|cafearticle|image|encyc|kin",
  "published_at": "2026-03-18T12:00:00+09:00",
  "score": 0.0
}
```

Source-specific fields are added without breaking the common shape.

### Composite Tool Policy

`search_naver_auto` is allowed to route across multiple sources, but it must:

- expose the selected intent
- list the sources used
- keep merge rules simple and documented

Composite tools are helpers. Low-level tools remain first-class.

Book and shopping intents use `web` and `blog` fallback sources because the dedicated upstream APIs no longer exist. The response includes `meta.fallback` and `meta.fallback_reason` so clients can distinguish fallback results.

## Reliability Policy

- Socket timeouts should fail fast without an immediate retry.
- Temporary 5xx responses may be retried once by default.
- Daily quota errors should not be retried automatically.
- Errors should include a stable error code and retryable flag.
- Cache should be conservative, time-bounded, and limited to 1,024 entries with LRU eviction.
- Credential errors should surface clearly.
- Upstream API responses should be type- and range-checked before normalization and caching.
- Upstream redirects must preserve scheme, host, and effective port before authentication headers are forwarded.
- HTTP servers should bind to loopback by default.
- Non-loopback binding requires FastMCP authentication or an operator-confirmed firewall/VPN allowlist.

## Cache Guidance

Recommended defaults:

- search: 5 minutes
- spell/adult detection: 30 minutes
- DataLab trends: 30 minutes or longer

Setting `NAVER_CACHE_TTL_SEC=0` disables all Search API tool caching, including
spell and adult-query results. DataLab keeps its documented 30-minute minimum.

Expired entries are pruned during writes, and the least recently used entry is
evicted when the in-memory cache reaches its 1,024-entry limit.

## Integration Guidance

Clients should choose one of two patterns:

### Pattern A. Direct deterministic use

Use low-level tools directly when the intent is obvious.

Examples:

- place search
- recipe lookup
- simple news lookup

### Pattern B. Orchestrated use

Let an orchestrator decide when to call this MCP server together with others.

Examples:

- multi-domain assistant responses
- answers requiring internal data plus public search data

This repository should support both patterns cleanly.
