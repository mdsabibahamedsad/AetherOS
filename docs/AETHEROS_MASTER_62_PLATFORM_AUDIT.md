# AETHEROS Master 62 — Platform Audit

Date: 2026-09-09. Branch state: `aetheros==0.16.0`, Python `>=3.11,<3.14`.
Method: full file reads of the platform surface + live test execution
(`tests/aetheros_platform/`, `tests/test_sdk.py`, TS SDK `npm test`).

## 1. Current architecture (verified)

```
Developer API (FastAPI, aetheros_platform/gateway.py:83 create_app)
↓  X-API-Key/Bearer → scope check → rate limit → idempotency → audit
SDKs: aetheros_sdk (sync+async, httpx) · sdks/typescript (@aetheros/sdk, zero-dep)
↓
Intent → PolicyBridge (aetheros_platform/policy.py) → capability resolution
↓  consults aetheros_security.policy (signal, deny-by-default locally)
AgentRuntime: AgentRegistry (11-state lifecycle) · ToolRegistry · SkillRegistry
↓
Execution: in-process tools (deadline-bounded) · MCP stdio · A2A HTTP · cron
↓
Storage/Audit/Artifacts: aetheros_data (SQLite: records/audit/artifacts/api_keys)
Events: EventBus + signed Webhooks (HMAC, replay window, retry, dead-letter)
```

## 2. Existing APIs (all exercised by tests, not just imported)

| Surface | Location | Status |
|---|---|---|
| Versioned REST `/api/v1` + `/api/v2` alias | `aetheros_platform/gateway.py` | IMPLEMENTED |
| Machine-readable registry (23 endpoints) | `aetheros_platform/registry.py` | IMPLEMENTED |
| Canonical schemas (34) + validation | `aetheros_platform/schemas.py` | IMPLEMENTED |
| TS bindings generator | `aetheros_platform/tsgen.py` | IMPLEMENTED (fixed: emitted 13/34, now all) |
| API-key auth (scrypt, display-once, rotate/revoke/expiry) | `aetheros_platform/auth.py` | IMPLEMENTED |
| Typed errors (25 categories) | `aetheros_platform/errors.py` | IMPLEMENTED |
| Rate limits (5 layers + concurrency cap) | `aetheros_platform/ratelimit.py` | IMPLEMENTED, enforced |
| Agents (manifest, lifecycle, quarantine) | `aetheros_platform/agents.py` | IMPLEMENTED |
| Tools (safety metadata, least-privilege invoke) | `aetheros_platform/tools.py` | IMPLEMENTED (fixed: excess-grant denial) |
| Skills (deps, cycles, anti-escalation) | `aetheros_platform/skills.py` | IMPLEMENTED |
| MCP scaffold + stdio list/call (proto 2025-11-25) | `aetheros_platform/mcp.py` | IMPLEMENTED |
| A2A card/validate/task store/HTTP client | `aetheros_platform/a2a.py` | EXPERIMENTAL subset |
| Packages `.aether-*` + local registry | `aetheros_platform/packages.py` | IMPLEMENTED (fixed: traversal/zip-slip) |
| Dev sandbox (isolated HOME/env/timeout) | `aetheros_platform/sandbox.py` | PARTIALLY (no containers) |
| Model router + labeled mock provider | `aetheros_platform/domains.py` | IMPLEMENTED |
| Memory/artifact/automation adapters | `aetheros_platform/domains.py` | IMPLEMENTED |
| Observability collectors | `aetheros_platform/observability/` | IMPLEMENTED |
| Dashboard HTTP/WS server, panels, widgets | `aetheros_platform/dashboard/` | EXPERIMENTAL (not E2E-proven here) |
| Desktop bridge/tray/window/notify | `aetheros_platform/desktop/` | EXPERIMENTAL (not E2E-proven here) |
| Standalone dev CLI (init/dev/schema/api/test/package/auth) | `aetheros_platform/cli.py` | IMPLEMENTED |
| Plugin/extension SDK (`.aep`, lifecycle, perms) | `sdk/` | IMPLEMENTED (fixed: ed25519 verify stub) |
| Python dev client | `aetheros_sdk/` | IMPLEMENTED (extended: artifacts/automations/webhooks/tasks) |
| TypeScript SDK | `sdks/typescript/` | IMPLEMENTED (extended + live-tested) |

## 3. Reusable components (extended, not duplicated)

`tools/registry.py` (tool discovery), `aetheros_security.policy` (policy
signal), `aetheros_security.tool_authz` (model-tool authz),
`aetheros_data` (records/audit/artifacts/api_keys), `cron/` (scheduler),
`agent/memory_provider.py` ABC, `ProviderProfile` registry, `sdk/`
(validator/packaging/permissions/lifecycle/versioning/compatibility).

## 4. Duplicate systems (kept separate deliberately)

- `aetheros_developer_platform/` (legacy in-process mocks: canned agent
  outputs, `publish` that prints) vs `aetheros_platform/` (real HTTP).
  Verdict: do NOT merge; the legacy tree is aspirational mock surface.
  Documented as such; no new code may import it as production.
- `gateway/run.py` (messaging gateway) vs `aetheros_platform/gateway.py`
  (developer HTTP API) vs `aetheros_cli/web_server.py` (dashboard :9119).
  Three servers, three jobs — kept, documented per surface.

## 5. Unsafe boundaries found and fixed this phase

1. `ToolRegistry.invoke` accepted caller grants exceeding the tool's
   declared capabilities (authority laundering). Fixed: excess grants →
   `CAPABILITY_NOT_GRANTED`; `run_task` narrows delegation to
   agent∩tool capabilities (`agents.py`, `tools.py`).
2. `POST /api/v1/tools` returned `200 ok` without validating anything.
   Fixed: schema-validate (422) then honest 403 (code upload disabled).
3. `build_package/publish/install` accepted `../../evil` names and
   unsafe zip paths. Fixed: strict identity + zip-slip guard.
4. `sdk/signing.py::verify_signature` ed25519 path was `pass→return True`.
   Fixed: real verification (raw-hex + OpenSSH formats); unknown
   algorithms raise instead of trusting.
5. `GET /tasks/{id}` returned a static stub; cancel never checked
   existence. Fixed: in-process task ledger with 404s.

## 6. Missing developer primitives (honest status)

- OAuth2/OIDC/mTLS: NOT_IMPLEMENTED (`auth.py` says so; scopes are the
  implemented mechanism).
- Remote marketplace registry + signature enforcement:
  UNAVAILABLE (local/test registry only; `signature: none-available`
  disclosed on every entry).
- Production sandbox (containers/seccomp): UNAVAILABLE (dev sandbox only).
- Approval service API, task pause/resume, replay debugger: NOT
  implemented (policy outcomes + audit trail exist; no standalone service).
- MCP 2026-07-28 features (stateless core, Tasks, extensions):
  BLOCKED on installed `mcp==1.26.0` (2025-11-25). No hard-coded claims.
- Main-binary `aetheros dev`: BLOCKED by pre-existing startup crash
  (`conflicting subparser: agent` — `aetheros_cli/agent_network_cmd.py:34`
  vs `agents/cli.py:445`; verified `python -m aetheros --help` crashes).

## 7. Migration / compatibility risks

- `ToolRegistry.invoke` is now strict about excess grants: direct API
  callers must pass only the invoked tool's capabilities (remediation in
  every error). `run_task` narrows automatically — no break there.
- `POST /api/v1/tools` behavior change: 200→422/403. No test or caller
  depended on the old 200.
- Schemas added 20 definitions; `generated.ts` grew 13→34 interfaces.
  No required-field tightening on existing schemas — wire compatible.
