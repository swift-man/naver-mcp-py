# naver-mcp-py

Python FastMCP server and reusable client library for Naver Search API and DataLab.

The current codebase is designed to run cleanly on Linux servers with Python 3.9+ and uses the standard library HTTP stack for API calls.

## Goals

- Expose Naver Search API and DataLab through MCP tools.
- Keep source normalization inside this repository.
- Support both MCP server mode and direct Python library mode.
- Provide a stable contract that app clients can depend on.

## Scope

This repository owns:

- Naver Open API client code
- DataLab client code
- Retry, timeout, cache, and validation
- HTML stripping and normalized response schemas
- FastMCP server implementation
- Tests for normalization and tool contracts

This repository does not own:

- KakaoTalk-specific reply formatting
- Room or thread policies
- Persona prompts
- End-user chat orchestration across multiple MCP servers

## Implemented Tools

Search tools:

- `search_local`
- `search_blog`
- `search_web`
- `search_news`
- `search_cafearticle`
- `spell_check`
- `detect_adult_query`
- `search_naver_auto`

DataLab tools:

- `datalab_search_trends`
- `datalab_shopping_category_trends`
- `datalab_shopping_device_trends`

## Project Layout

```text
naver-mcp-py/
  README.md
  AGENTS.md
  ARCHITECTURE.md
  TOOL_CONTRACT.md
  pyproject.toml
  .env.example
  sitecustomize.py
  src/naver_mcp/
    __init__.py
    cache.py
    client.py
    config.py
    errors.py
    models.py
    normalize.py
    server.py
    tools_datalab.py
    tools_search.py
  tests/
    test_normalize.py
    test_tools_datalab.py
    test_tools_search.py
```

## Quick Start

### 1. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

For server runtime:

```bash
pip install -U pip
pip install -e ".[server]"
```

For local development:

```bash
pip install -U pip
pip install -e ".[server,dev]"
```

### 3. Configure environment

Available environment variables:

- `NAVER_CLIENT_ID`
- `NAVER_CLIENT_SECRET`
- `NAVER_MCP_HOST`
- `NAVER_MCP_PORT`
- `NAVER_MCP_PATH`
- `NAVER_MCP_TRANSPORT`
- `NAVER_HTTP_TIMEOUT_SEC`
- `NAVER_CACHE_TTL_SEC`

You can use `.env.example` as a template, but the current code does not auto-load `.env`.
On Linux servers, export the variables explicitly or load them through your process manager such as `systemd`.

### 4. Run the MCP server

```bash
python3 -m naver_mcp.server
```

Default MCP endpoint:

- `http://127.0.0.1:8100/mcp`

`healthz()` is also exposed as a plain Python helper for embedding or wrapper HTTP apps.

## Linux Deployment Note

Recommended production pattern:

1. Keep the service bound to `127.0.0.1`.
2. Load secrets through `systemd EnvironmentFile` or another secret manager.
3. Put `nginx` or another reverse proxy in front if external access is needed.

## Design Principles

- Keep tool inputs simple and explicit.
- Normalize response shapes before returning from tools.
- Preserve source-specific fields without breaking the common contract.
- Make search tools deterministic where possible.
- Treat composite tools such as `search_naver_auto` as convenience tools, not replacements for low-level tools.

## Testing

Recommended commands:

```bash
python3 -m unittest discover -s tests
ruff check .
PYTHONPYCACHEPREFIX=/tmp/naver-mcp-py-pyc python3 -m py_compile sitecustomize.py src/naver_mcp/*.py tests/*.py
```

Prefer mock-based tests for API contracts and normalization. Keep live API checks optional.

## Integration Model

Typical deployment uses this repository as one MCP server among several:

```text
chat app -> app router or orchestrator -> naver-mcp-py
```

The chat app is responsible for channel-specific rendering. This repository is responsible for structured retrieval.

## Documentation

- Architecture: [ARCHITECTURE.md](ARCHITECTURE.md)
- Tool contract: [TOOL_CONTRACT.md](TOOL_CONTRACT.md)
- Agent guidance: [AGENTS.md](AGENTS.md)
