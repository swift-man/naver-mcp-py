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
- `search_image`
- `search_book`
- `search_book_advanced`
- `search_encyc`
- `search_kin`
- `search_shop`
- `search_doc`
- `spell_check`
- `detect_adult_query`
- `search_naver_auto`

DataLab tools:

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

Notes:

- `datalab_shopping_device_trends` is kept as a backward-compatible alias of `datalab_shopping_category_device_trends`
- `search_book_advanced` wraps the Naver advanced book lookup and requires at least `title` or `isbn`

## Project Layout

```text
naver-mcp-py/
  README.md
  AGENTS.md
  pyproject.toml
  .env.example
  sitecustomize.py
  docs/
    ARCHITECTURE.md
    TOOL_CONTRACT.md
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

## Requirements

- Python 3.9+
- Naver Search API credentials
- Naver DataLab API access
- Linux server only if you plan to run it as a long-lived service

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

Security note:

- never commit real `NAVER_CLIENT_ID` or `NAVER_CLIENT_SECRET`
- keep real credentials only in private shell exports, `.env` files excluded by `.gitignore`, or `/etc/naver-mcp.env`
- if a real key was ever pushed to a public repository, rotate it immediately in the Naver developer console

Example:

```bash
export NAVER_CLIENT_ID="your_client_id"
export NAVER_CLIENT_SECRET="your_client_secret"
export NAVER_MCP_HOST="127.0.0.1"
export NAVER_MCP_PORT="8100"
export NAVER_MCP_PATH="/mcp"
export NAVER_MCP_TRANSPORT="streamable-http"
export NAVER_HTTP_TIMEOUT_SEC="8.0"
export NAVER_CACHE_TTL_SEC="300"
```

### 4. Run the MCP server

```bash
python3 -m naver_mcp.server
```

Default MCP endpoint:

- `http://127.0.0.1:8100/mcp`

`healthz()` is also exposed as a plain Python helper for embedding or wrapper HTTP apps.

## Manual Run On Linux

If you are running the server by hand on a Linux machine:

```bash
cd /path/to/naver-mcp-py
python3 -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install -e ".[server]"

export NAVER_CLIENT_ID="your_client_id"
export NAVER_CLIENT_SECRET="your_client_secret"
export NAVER_MCP_HOST="127.0.0.1"
export NAVER_MCP_PORT="8100"
export NAVER_MCP_PATH="/mcp"
export NAVER_MCP_TRANSPORT="streamable-http"
export NAVER_HTTP_TIMEOUT_SEC="8.0"
export NAVER_CACHE_TTL_SEC="300"

.venv/bin/python -m naver_mcp.server
```

If an MCP client runs on a different machine and must connect over the LAN:

- set `NAVER_MCP_HOST=0.0.0.0`
- open the port in your firewall if needed
- make sure the client uses the same path as `NAVER_MCP_PATH`

For example, if the client connects to `http://192.168.1.218:8100/naver_mcp`, then your environment must include:

```bash
export NAVER_MCP_HOST="0.0.0.0"
export NAVER_MCP_PATH="/naver_mcp"
```

## Linux Server Deployment With systemd

Recommended production pattern:

1. Keep the service bound to `127.0.0.1`.
2. Load secrets through `systemd EnvironmentFile` or another secret manager.
3. Put `nginx` or another reverse proxy in front if external access is needed.

Example deployment directory:

```bash
/home/<USER>/naver-mcp-py
```

### 1. Prepare the project

```bash
cd /home/<USER>/naver-mcp-py
python3 -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install -e ".[server]"
```

### 2. Create the environment file

Create `/etc/naver-mcp.env`:

```bash
sudo tee /etc/naver-mcp.env > /dev/null <<'EOF'
NAVER_CLIENT_ID=your_client_id
NAVER_CLIENT_SECRET=your_client_secret
NAVER_MCP_HOST=127.0.0.1
NAVER_MCP_PORT=8100
NAVER_MCP_PATH=/mcp
NAVER_MCP_TRANSPORT=streamable-http
NAVER_HTTP_TIMEOUT_SEC=8.0
NAVER_CACHE_TTL_SEC=300
EOF
```

This file should stay on the server only and must not be copied into the repository.

If your MCP client connects over the network directly, update these two values:

```bash
NAVER_MCP_HOST=0.0.0.0
NAVER_MCP_PATH=/naver_mcp
```

The client URL must exactly match the path you configure here.

### 3. Create the systemd unit

Create `/etc/systemd/system/naver-mcp.service`:

```ini
[Unit]
Description=Naver MCP Python Server
After=network.target

[Service]
Type=simple
User=<USER>
WorkingDirectory=/home/<USER>/naver-mcp-py
EnvironmentFile=/etc/naver-mcp.env
ExecStart=/home/<USER>/naver-mcp-py/.venv/bin/python -m naver_mcp.server
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Notes:

- `User` must be a real Linux user
- `WorkingDirectory` must match the actual repository path
- `ExecStart` must point to the actual virtualenv Python
- in most cases you do not need a `Group=` line

### 4. Start the service

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now naver-mcp
sudo systemctl status naver-mcp --no-pager
```

### 5. Check logs and listening port

```bash
journalctl -u naver-mcp -f
ss -ltnp | grep 8100
```

## MCP Client URL

The client URL must match both the host, port, and path from your environment.

Examples:

- default local setup: `http://127.0.0.1:8100/mcp`
- LAN exposure with custom path: `http://192.168.1.218:8100/naver_mcp`

If the client uses `/naver_mcp` but the server is configured with `/mcp`, requests will fail even if the process is running.

## Troubleshooting

### `ECONNREFUSED`

This usually means nothing is listening on that IP and port.

Check:

```bash
sudo systemctl status naver-mcp --no-pager
ss -ltnp | grep 8100
```

Common causes:

- service is not running
- `NAVER_MCP_HOST` is `127.0.0.1` but you are connecting from another machine
- firewall is blocking the port

### `status=203/EXEC`

This means `ExecStart` points to a missing or non-executable path.

Check:

```bash
ls -l /home/<USER>/naver-mcp-py/.venv/bin/python
```

### `status=216/GROUP`

This usually means the `Group=` value in the systemd unit is invalid.

Fix:

- remove the `Group=` line, or
- change it to a real group from `id <USER>`

### Wrong MCP path

If the client connects to:

```text
http://SERVER_IP:8100/naver_mcp
```

then you must configure:

```bash
NAVER_MCP_PATH=/naver_mcp
```

If you keep the default:

```bash
NAVER_MCP_PATH=/mcp
```

then the client must use:

```text
http://SERVER_IP:8100/mcp
```

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

- Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Tool contract: [docs/TOOL_CONTRACT.md](docs/TOOL_CONTRACT.md)
- Agent guidance: [AGENTS.md](AGENTS.md)
