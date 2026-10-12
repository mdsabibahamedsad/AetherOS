# AetherOS Agent Network — Repository Audit (Master 46, Phase A)

Date: 2026-09-05 · Auditor: Principal Distributed AI Architect · Scope: read-only inspection of `aetheros/` checkout.

## 1. What already exists (with evidence)

### 1.1 Local agent orchestration (Master 42 lineage)
- `agent/orchestration/agent_registry.py` — `AgentRegistration` / `AgentInstance` / `AgentRegistry` (asyncio-locked, role/capability/tag indexes, health checks). **Local-only**: factories are in-process callables; no network transport, no identity crypto, no trust levels.
- `aetheros_swarm/registry.py` — `AgentDefinition` × 16 Master-42 roles + `AgentRegistry.discover/match/find_by_capability`. **Local-only**: capability-driven role selection, no remote endpoints.
- `aetheros_swarm/orchestrator.py:493` delegates via `tools/delegate_tool.py` (`delegate_task`, sync, capped, non-durable). No idempotency keys, no cross-instance tasks.
- `agents/runtime.py:214,263` — fallback to `delegate_task`. `agents/web.py:203` — `delegate_task_api(from_agent, to_agent, goal)` is an **in-process** handoff, not a network protocol.

### 1.2 Communication fabric identity (closest to A2A Agent Card)
- `aetheros_comm/identity.py` — `AgentCard` dataclass (`agentId, name, description, version, capabilities, supportedTasks, supportedProtocols, supportedTransports, authenticationMethods, requiredPermissions, trustZone, healthEndpoint, status`) + `AgentRegistry` (`identity.py:232`) with registration validation (identity, version, capabilities, security posture, protocol versions, health, config). Mirrors into `aetheros_security.identity`.
- Gap: card is **self-declared**; no signature field, no issuer/CA pinning, no expiration/revocation, no `/.well-known/` fetch, no A2A field names (`url`, `skills`, `defaultInputModes`…).

### 1.3 Remote-instance platform (NOT A2A)
- `REMOTE_AGENTS.md` (v0.23.0) + `aetheros_cli/remote_agent_platform.py` (1148 lines) — controller/node model: mTLS + short-lived bearer tokens, health checks, log streaming, workspace bridge, auto-reconnect with backoff/jitter, rate limiting, audit events (`remote.*`).
- Gap: proprietary controller/node protocol. No Agent Card, no task delegation across vendors, no federation, no capability-scoped authz beyond admin/operator/viewer.

### 1.4 Security primitives available for reuse
- `aetheros_security/identity/` — principal registry, trust levels, status (active/suspended/quarantined/revoked/expired).
- `aetheros_security/network/` — `NetworkSecurityManager`: host allow/deny, port policy, private-CIDR blocking, TLS-verify flag. Directly reusable for SSRF defense.
- `aetheros_security/approval/`, `authz/`, `dlp/`, `classification/`, `redaction/`, `secrets/`, `tokens/`, `rate_limit/`, `audit/`, `kill_switch/` — all present; agent-network must **integrate**, not duplicate.
- `agent/authorization_engine.py:300,564` — `tool:delegate_task` permission mapping exists.

### 1.5 Gateway / server / IPC surfaces
- `gateway/run.py` + `gateway/platforms/` (~20 adapters) — messaging gateway, not an agent-protocol gateway. Has `authz_mixin.py`, `pairing.py`, `status.py` (scoped locks for token sharing across profiles).
- `tui_gateway/server.py` (11k lines) — stdio JSON-RPC for the TUI/Electron backend. Extension point for `agent.network.*` typed IPC.
- `aetheros_cli/web_server.py` + `pty_bridge.py` — dashboard embeds `aetheros --tui`; do not build a second chat surface.
- `aetheros_cli/_parser.py` + `main.py` — CLI pattern: `build_parser(subparsers)` + `set_defaults(func=...)` (see `portal_cli.add_parser`, `kanban.build_parser`).

### 1.6 Desktop
- `apps/desktop/src/store/remote-agent.ts` — remote-instance atoms. **Warning:** `connect()` just flips status to `online` with no network I/O; `startAgent()` flips to `running` locally. This is exactly the "fake remote agent" class Master 46 §0.4 forbids — the new `agent-network.ts` store must be IPC-backed and must surface `UNVERIFIED/OFFLINE` honestly.
- `apps/desktop/src/store/agent-hub.ts` — local agent templates/configs (coding/research/…). No remote concepts.
- Routes in `apps/desktop/src/app/routes.ts`; no `/agent-network` route exists.

### 1.7 MCP / extensions / models / memory / automation integration points
- `tools/registry.py` + `toolsets.py` (`TOOLSETS` dict) — MCP/tool exposure is toolset-gated. Remote agents must request capabilities through policy, never get toolsets directly.
- `plugins/` + `aetheros_cli/plugins.py` (`ctx.register_tool`) — extension route for connectors.
- Master 45 model router, Master 43 `cron/jobs.py` + `scheduler.py` (3-min hard interrupt, file lock, `skip_memory=True`), Master 41 memory providers (`plugins/memory/`, closed set), Master 40 research evidence (`claim/source/timestamp/provenance/agent/citation`).

## 2. A2A / federation search results
- No `a2a_*` module, no `/.well-known/agent-card`, no `message/send`, no JSON-RPC task transport exists in the tree.
- `aetheros_comm/protocol.py:SUPPORTED_PROTOCOL_VERSIONS` is the internal fabric version, not A2A.
- Conclusion: **greenfield A2A layer** reusing §1.4 primitives. No competing registry to merge with for *remote* agents; the local registries (§1.1–1.2) stay authoritative for local agents and the new `aetheros_network/registry.py` stores only remote/federated records with provenance, referencing local IDs where they overlap.

## 3. Risks / constraints carried into design
1. Prompt-caching sacred (§AGENTS.md): network activity must not mutate conversation context mid-loop; discovery/trust changes take effect next session unless `--now`.
2. Core narrow waist: no new model tools; remote delegation surfaces as CLI + skill + `AgentGateway` API, not core-tool schema.
3. `~/.aetheros` never hardcoded — `get_aetheros_home()` / `display_aetheros_home()` everywhere; tests use temp `AETHEROS_HOME`.
4. `.env` secrets-only; all behavior flags in `config.yaml` (`agent_network:` section).
5. `scripts/run_tests.sh` is the only supported test entrypoint.
6. Desktop `remote-agent.ts` fake-status pattern must NOT be copied.

## 4. Build order (maps to Master 46 §157)
B identity → C card → D discovery → E registry → F trust → G auth → H authz → I transport → J tasks → K streaming → L artifacts → M security/DLP → N gateway → O server → P–U integrations → V federation → W desktop → X CLI → Y adversarial → Z interop → AA perf → AB docs → AC cert.
