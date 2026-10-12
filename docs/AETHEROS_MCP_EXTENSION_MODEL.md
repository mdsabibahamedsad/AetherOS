# MCP Extension Model (Master 44)

Every configured MCP server is representable as an MCPExtension
(`mcp.<id>`) with `mcp.connect` + `mcp.tool.execute` scoped grants.
Lifecycle reuses the single extension lifecycle; health is read from the
real MCP client (`connected` / `configured-but-idle` / `unconfigured` —
never fabricated).

Server trust ≠ tool trust: a signed server with a poisoned tool
description is still gated (description scan + per-invocation policy/
permission/approval/risk). Transports: stdio/process/HTTP-SSE/
streamable HTTP via the existing client; auth from existing config
(secrets never logged — client strips credentials in errors).

Remote MCP = untrusted source policy; unsigned/dev rules apply to the
extension record, connection auth stays in user config.
