# A2A Architecture (Master 46)

## Layering

```
AetherOS Agent
  |-- MCP -----> GitHub / Browser tools / Database   (tools, data, context)
  |-- A2A -----> Research Agent / Coding Agent        (agent to agent)
```

A2A is strictly agent↔agent. MCP servers are never auto-converted into
A2A agents, and internal MCP tools are never exposed to remote agents
except through an explicit, approved capability request evaluated by
`aetheros_network/policy.py` and executed locally.

## Protocol scope (honest)

Target: **A2A v1.0 core subset**.

| Feature | Status |
|---|---|
| Agent Card fetch (`/.well-known/agent-card.json`) | implemented |
| Card parse v1.0 (`protocolVersion`) | implemented |
| Card parse legacy v0.3 (`protocolVersions`) | normalized, version recorded |
| `message/send` | implemented (idempotency-keyed) |
| `tasks/get`, `tasks/cancel` | implemented |
| `message/stream` (SSE) | implemented client-side |
| Protocol negotiation (`protocolVersion` echo) | partial: accept 1.0/0.3, reject others explicitly |
| Push notifications / webhooks | **not implemented** |
| mDNS / DNS-SD discovery | **not implemented** (explicit LAN registry + URL instead) |
| OAuth2/OIDC validation | structural (scheme allowlist); full token validation is deployment-configured, **not blindly claimed** |
| mTLS client certs | transport supports CA bundle + pinning fields; full mTLS handshake policy lives with the existing controller/node platform (`REMOTE_AGENTS.md`) |

Unsupported versions are rejected loudly, never silently downgraded.

## Module map (`aetheros_network/`)

| Module | Responsibility |
|---|---|
| `identity.py` | canonical `AgentIdentity`, Ed25519 keys, fingerprints, signatures |
| `agent_card.py` | parse/normalize/validate, endpoint-consistency + injection-flag warnings |
| `trust.py` | trust levels, allowed transitions, persisted `TrustStore` |
| `registry.py` | remote-agent records, provenance, re-verify flags, removal preserves history |
| `discovery.py` | direct URL, manual import, registry files (all UNTRUSTED) |
| `transport.py` | HTTPS JSON-RPC client, SSRF guard, timeouts, idempotency, SSE |
| `policy.py` | permission catalog, authz, classification, DLP, injection screens, URL policy |
| `tasks.py` | `RemoteTask` state machine, SQLite persistence, reconcile, bounded queue |
| `artifacts.py` | integrity, quarantine, traversal/bomb/executable defense |
| `router.py` | capability/trust/privacy/latency/cost/SLA routing + decision traces |
| `gateway.py` | facade: pairing, delegation pipeline, rate limits, circuit breaker, audit |
| `server.py` | deny-by-default A2A server (stdlib http) |
| `audit.py` | append-only JSONL audit (payloads summarized, never secrets) |
| `ipc.py` | validated `agent.network.*` handlers for tui_gateway/Electron |
| `aetheros_cli/agent_network_cmd.py` | `aetheros agent ...` CLI |

Security is enforced in `policy.py` + `gateway.py` + `transport.py`,
below any UI. The desktop store (`agent-network.ts`) and page are
read-through views over `agent.network.*` IPC — they hold no credentials
and fabricate no state.
