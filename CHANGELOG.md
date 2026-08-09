# Changelog

All notable changes to this project are documented in this file.

## [0.2.0.0] - 2026-08-09

### Added

- Added NAVER API HUB credentials, request headers, and endpoint support for Search, Search Trend, and Shopping Insight APIs.
- Added API HUB client contract tests and an opt-in live smoke test that reads credentials only from environment variables.
- Added structured service-unavailable errors for the upstream search APIs that Naver retired on 2026-07-31.

### Changed

- Updated Search Trend filters, group limits, and local search limits to match the API HUB contracts.
- Changed book and shopping intent routing in `search_naver_auto` to use disclosed web and blog fallbacks.
- Updated Linux and systemd setup instructions for the new credentials and API base URL.
- Kept the legacy credential environment variable names as compatibility aliases.
- Require an explicit authenticated or trusted-network mode before binding HTTP to a non-loopback address.
- Require FastMCP 3.4.6 or newer within the 3.x line for supported JWT authentication and security fixes.

### Fixed

- Retry temporary 5xx failures while returning authentication and daily-quota errors without an immediate retry.
- Return structured MCP errors for validation, authentication, quota, timeout, and retired-service failures.
- Reject scalar DataLab list inputs and reversed date ranges before sending an API request.
- Prevent arbitrary long numeric queries from being classified as ISBN searches without a valid checksum.
- Reject invalid DataLab response elements, out-of-range ratios, malformed errata values, unsafe API base URLs, invalid timeout values, and non-integer pagination inputs.
