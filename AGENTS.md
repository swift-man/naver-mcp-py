# AGENTS.md

This repository is a Python MCP server for Naver APIs.

## Mission

Build a small, reliable, reusable MCP server that exposes Naver Search API and DataLab through stable tool contracts.

## Priority Order

1. Tool contract stability
2. Clear normalization
3. Predictable behavior
4. Simple operations
5. Breadth of features

## What This Repository Owns

- Naver API client code
- Response normalization
- MCP tool implementation
- Validation, timeout, retry, and cache behavior
- Tests for normalization and tool contract correctness

## What This Repository Does Not Own

- KakaoTalk message formatting
- End-user conversational prompts
- Multi-MCP orchestration policy
- Room-specific business rules

## Coding Guidelines

- Prefer plain Python modules over premature abstraction.
- Keep low-level API client logic separate from MCP tool functions.
- Return normalized dictionaries or typed models that can be serialized cleanly.
- Strip HTML from Naver responses before returning user-facing fields.
- Preserve raw source fields only when they add integration value.
- Avoid hidden heuristics in low-level tools.

## Tool Design Rules

- Low-level tools must map closely to source APIs.
- Composite tools must clearly declare which sources they used.
- All tools should return a `meta` block when practical.
- Validation errors should be explicit and structured.
- Timeouts should fail fast with retryability information.

## Testing Rules

- Add tests for every normalization helper.
- Add contract tests for every MCP tool.
- Prefer fixtures or mocked HTTP responses over live network tests.
- Keep one optional smoke test path for real credentials if needed, but do not require it in CI.

## File Ownership Hints

- `client.py`: Naver HTTP client only
- `normalize.py`: response cleanup and schema shaping
- `tools_search.py`: search-related MCP tools
- `tools_datalab.py`: DataLab MCP tools
- `server.py`: FastMCP setup and tool registration
- `models.py`: shared request and response models

## When Extending the Repository

- Update `TOOL_CONTRACT.md` before or with code changes.
- Keep `README.md` aligned with actual startup commands.
- Do not add chat-app assumptions into tool outputs.
- If a new tool mixes multiple sources, document ranking and merge rules.

## First Steps For A New Codex Session

1. Read `README.md`.
2. Read `ARCHITECTURE.md`.
3. Read `TOOL_CONTRACT.md`.
4. Inspect the current file tree and tests.
5. Implement the smallest vertical slice first.

