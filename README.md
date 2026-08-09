# naver-mcp-py

Python FastMCP server and reusable client library for NAVER API HUB Search,
Search Trend, and Shopping Insight APIs.

The current codebase is designed to run cleanly on Linux servers with Python 3.10+ and uses the standard library HTTP stack for API calls.

## Goals

- Expose NAVER API HUB Search and DataLab features through MCP tools.
- Keep source normalization inside this repository.
- Support both MCP server mode and direct Python library mode.
- Provide a stable contract that app clients can depend on.

## Scope

This repository owns:

- NAVER API HUB client code
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

Supported search tools:

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

Retired upstream search tools kept for contract compatibility:

- `search_book`
- `search_book_advanced`
- `search_shop`
- `search_doc`

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
- Naver ended book, shopping product, and professional document search on 2026-07-31 without replacement APIs
- retired tools fail immediately with `NAVER_SERVICE_UNAVAILABLE` and do not make network requests
- book and shopping intents in `search_naver_auto` fall back to web and blog search and disclose that fallback in `meta`

## NAVER API HUB

This project uses the NAVER API HUB endpoint and authentication scheme introduced in 2026:

```text
API URL: https://naverapihub.apigw.ntruss.com
Client ID header: X-NCP-APIGW-API-KEY-ID
Client Secret header: X-NCP-APIGW-API-KEY
```

Register an application under `Application Services > NAVER API HUB` and enable the APIs you need. Credentials issued for the separate AI NAVER API product may not have NAVER API HUB permissions.

Official references:

- [NAVER API HUB overview](https://api.ncloud-docs.com/docs/naver-api-hub-overview)
- [Search API migration notice](https://developers.naver.com/notice/article/32530)
- [Search keyword trends](https://api.ncloud-docs.com/docs/naver-api-hub-search-trend)
- [Shopping Insight](https://api.ncloud-docs.com/docs/naver-api-hub-shopping-insight-categories)

## Project Layout

```text
naver-mcp-py/
  README.md
  CHANGELOG.md
  VERSION.txt
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
    test_client.py
    test_normalize.py
    test_server.py
    test_smoke_live.py
    test_tools_datalab.py
    test_tools_search.py
```

## Requirements

- Python 3.10+
- NAVER API HUB Client ID and Client Secret
- Search, Search Trend, and Shopping Insight permissions selected for the application
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

- `NAVER_API_HUB_CLIENT_ID`
- `NAVER_API_HUB_CLIENT_SECRET`
- `NAVER_API_BASE_URL` (optional; defaults to `https://naverapihub.apigw.ntruss.com`; HTTPS required except for loopback testing)
- `NAVER_MCP_HOST`
- `NAVER_MCP_PORT`
- `NAVER_MCP_PATH`
- `NAVER_MCP_TRANSPORT`
- `NAVER_MCP_REMOTE_ACCESS` (optional; `disabled`, `fastmcp-auth`, or `trusted-network`)
- `NAVER_MCP_AUTH_JWKS_URI`, `NAVER_MCP_AUTH_ISSUER`, and `NAVER_MCP_AUTH_AUDIENCE` when using JWT authentication
- `NAVER_HTTP_TIMEOUT_SEC`
- `NAVER_CACHE_TTL_SEC`

You can use `.env.example` as a template, but the current code does not auto-load `.env`.
On Linux servers, export the variables explicitly or load them through your process manager such as `systemd`.

Security note:

- issue credentials from `Application Services > NAVER API HUB`, not the separate AI NAVER API application menu
- never commit real `NAVER_API_HUB_CLIENT_ID` or `NAVER_API_HUB_CLIENT_SECRET`
- keep real credentials only in private shell exports, `.env` files excluded by `.gitignore`, or `/etc/naver-mcp.env`
- if a real key was ever pushed to a public repository, reissue it immediately in the NAVER Cloud Platform console
- legacy `NAVER_CLIENT_ID` and `NAVER_CLIENT_SECRET` variable names remain accepted as aliases, but the values must be NAVER API HUB credentials
- upstream `NAVER_API_BASE_URL` overrides must use HTTPS; plain HTTP is accepted only for explicit loopback hosts during local testing
- upstream redirects are followed only within the same scheme, host, and effective port so credentials cannot cross origins or downgrade to HTTP
- HTTP binding to a non-loopback address is refused unless authenticated FastMCP or an explicitly protected trusted network is configured

Example:

```bash
export NAVER_API_HUB_CLIENT_ID="your_client_id"
export NAVER_API_HUB_CLIENT_SECRET="your_client_secret"
export NAVER_MCP_HOST="127.0.0.1"
export NAVER_MCP_PORT="8100"
export NAVER_MCP_PATH="/mcp"
export NAVER_MCP_TRANSPORT="streamable-http"
export NAVER_MCP_REMOTE_ACCESS="disabled"
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

export NAVER_API_HUB_CLIENT_ID="your_client_id"
export NAVER_API_HUB_CLIENT_SECRET="your_client_secret"
export NAVER_MCP_HOST="127.0.0.1"
export NAVER_MCP_PORT="8100"
export NAVER_MCP_PATH="/mcp"
export NAVER_MCP_TRANSPORT="streamable-http"
export NAVER_MCP_REMOTE_ACCESS="disabled"
export NAVER_HTTP_TIMEOUT_SEC="8.0"
export NAVER_CACHE_TTL_SEC="300"

.venv/bin/python -m naver_mcp.server
```

The server refuses an HTTP bind to `0.0.0.0` or another non-loopback address by default. Choose one protected remote-access mode before connecting from another machine.

For a private LAN or VPN with a firewall source-IP allowlist:

- configure the host firewall or cloud security group to allow port `8100` only from the MCP client IP or VPN subnet
- set `NAVER_MCP_REMOTE_ACCESS=trusted-network`
- never use this mode on an unrestricted public network

For example, if the client connects to `http://192.168.1.218:8100/naver_mcp`, then your environment must include:

```bash
export NAVER_MCP_HOST="0.0.0.0"
export NAVER_MCP_PATH="/naver_mcp"
export NAVER_MCP_REMOTE_ACCESS="trusted-network"
```

For authenticated remote access, configure the FastMCP JWT verifier and use TLS. The following example validates JWTs from an existing identity provider:

```bash
export NAVER_MCP_HOST="0.0.0.0"
export NAVER_MCP_REMOTE_ACCESS="fastmcp-auth"
export NAVER_MCP_AUTH_JWKS_URI="https://auth.example.com/.well-known/jwks.json"
export NAVER_MCP_AUTH_ISSUER="https://auth.example.com"
export NAVER_MCP_AUTH_AUDIENCE="naver-mcp"
```

The server creates a FastMCP `JWTVerifier` from these values. See the [FastMCP token verification guide](https://gofastmcp.com/servers/auth/token-verification) for identity-provider and client setup. For internet-facing deployments, terminate TLS at an authenticated reverse proxy or load balancer and restrict direct access to port `8100`.

## Linux Server Deployment With systemd

Recommended production pattern:

1. Keep the service bound to `127.0.0.1`.
2. Load secrets through `systemd EnvironmentFile` or another secret manager.
3. Put an authenticated TLS reverse proxy in front if external access is needed.
4. Do not expose port `8100` publicly.

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
sudo install -m 600 -o root -g root /dev/null /etc/naver-mcp.env
sudo tee /etc/naver-mcp.env > /dev/null <<'EOF'
NAVER_API_HUB_CLIENT_ID=your_client_id
NAVER_API_HUB_CLIENT_SECRET=your_client_secret
NAVER_MCP_HOST=127.0.0.1
NAVER_MCP_PORT=8100
NAVER_MCP_PATH=/mcp
NAVER_MCP_TRANSPORT=streamable-http
NAVER_MCP_REMOTE_ACCESS=disabled
NAVER_HTTP_TIMEOUT_SEC=8.0
NAVER_CACHE_TTL_SEC=300
EOF
sudo chown root:root /etc/naver-mcp.env
sudo chmod 600 /etc/naver-mcp.env
sudo stat -c '%U:%G %a %n' /etc/naver-mcp.env
```

The verification output must show `root:root 600 /etc/naver-mcp.env`.

This file should stay on the server only and must not be copied into the repository.

If your MCP client connects directly over a firewall-restricted LAN or VPN, update these values only after creating a source-IP allowlist:

```bash
NAVER_MCP_HOST=0.0.0.0
NAVER_MCP_PATH=/naver_mcp
NAVER_MCP_REMOTE_ACCESS=trusted-network
```

The client URL must exactly match the path you configure here. Without `fastmcp-auth` or `trusted-network`, the service intentionally refuses a non-loopback bind.

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

### Update an existing Linux deployment

```bash
cd /home/<USER>/naver-mcp-py
git pull origin main
.venv/bin/pip install -e ".[server]"
sudoedit /etc/naver-mcp.env
sudo systemctl restart naver-mcp
sudo systemctl status naver-mcp --no-pager
```

When migrating from the old Naver developer API, replace the credential entries with `NAVER_API_HUB_CLIENT_ID` and `NAVER_API_HUB_CLIENT_SECRET` in the `sudoedit` step. Save them before running the restart command.

If an existing deployment uses a non-loopback host, also configure `NAVER_MCP_REMOTE_ACCESS=trusted-network` only after verifying its firewall/VPN allowlist, or migrate it to `fastmcp-auth`. Otherwise the updated service will refuse to start rather than expose an unauthenticated endpoint.

## MCP Client URL

The client URL must match both the host, port, and path from your environment.

Examples:

- default local setup: `http://127.0.0.1:8100/mcp`
- protected LAN/VPN exposure with custom path: `http://192.168.1.218:8100/naver_mcp`
- authenticated public endpoint through a TLS proxy: `https://naver-mcp.example.com/naver_mcp`

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
- non-loopback binding was refused because `NAVER_MCP_REMOTE_ACCESS` protection is missing

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

To run one real NAVER API HUB smoke test without exposing credentials in the repository:

```bash
export NAVER_LIVE_SMOKE_TEST=1
export NAVER_API_HUB_CLIENT_ID="your_client_id"
export NAVER_API_HUB_CLIENT_SECRET="your_client_secret"
python3 -m unittest tests.test_smoke_live
```

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
