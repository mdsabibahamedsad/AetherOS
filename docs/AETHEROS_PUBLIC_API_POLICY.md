# Public API Policy — What Is PUBLIC / INTERNAL / EXPERIMENTAL / DEPRECATED / PRIVATE / UNSTABLE

Source of truth: `aetheros_platform/registry.py::ENDPOINTS`
(registry version `1.0.0`; inspect live via `GET /api/v1/registry`).

## PUBLIC (stable, versioned, covered by contract tests)

Agents, tasks (+cancel, +SSE events), tools list/invoke, skills,
memory records/search, artifacts create/get, automations create,
webhooks register, registry/schemas/health. Auth: API key. Authz: scopes.

## EXPERIMENTAL (works, may change, never auto-trusted)

`GET /api/v1/a2a/card`, `POST /api/v1/a2a/tasks` (protocol
`0.3.0-compat`; remote agents default `untrusted`).
MCP server scaffold + stdio list/call (protocol 2025-11-25 via
`mcp==1.26.0`). Local/test package registry.

## INTERNAL

`aetheros_data` records, `AgentRepository`, `AuditLog`, `ArtifactStore`
internals, `AIAgent` loop, `handle_function_call`. Reachable only through
the gateway adapters — never directly from SDKs.

## DEPRECATED / PRIVATE / UNSTABLE

None shipped in registry 1.0. `/api/v2` is an alias of v1 (headers
`X-API-Version: v2-alias-of-v1`, `Sunset: not-planned`) for
version-negotiation tests — not a separate contract.

## Rules

- Nothing becomes PUBLIC without: schema + registry entry + scopes +
  rate limit + audit policy + contract test + docs entry.
- `POST /api/v1/tools` validates manifests but refuses code upload
  (403 `POLICY_DENIED`): executing uploaded code would bypass review.
- Tool/MCP/Agent-Card metadata is untrusted input: it never overrides
  policy (`tools.py` excess-grant denial; `a2a.py` trust set).
