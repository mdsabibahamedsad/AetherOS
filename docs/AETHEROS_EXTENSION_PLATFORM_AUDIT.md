# AetherOS Extension Platform — Repository Audit (Master 44, Phase A)

## Existing architecture (verified, not invented)

- **Skills**: `skills/<category>/<skill>/SKILL.md` with frontmatter
  (name, description, version, author, license, platforms, metadata.hermes).
  Skill tools: `tools/skills_hub.py` (sources: official optional, GitHub
  Contents API, HubLockFile provenance, quarantine dir), `tools/skills_guard.py`
  (regex static scanner + trust-aware install policy:
  builtin/trusted/community/agent-created), `tools/skills_tool.py`,
  `tools/skill_manager_tool.py`, `tools/skills_sync.py`, `tools/skill_usage.py`,
  `tools/skill_provenance.py`, `tools/skills_ast_audit.py`.
- **MCP**: `tools/mcp_tool.py` — full client (stdio, HTTP/StreamableHTTP,
  SSE), reconnect w/ backoff, env filtering, credential stripping,
  timeouts, sampling, parallel opt-in, thread-safe; config from
  `~/.aetheros/config.yaml` `mcp_servers`. OAuth: `mcp_oauth*.py`.
- **Tools**: `tools/registry.py` — `ToolRegistry` + `ToolEntry`
  (risk/permission/sandbox/retry/circuit/timeout metadata fields exist),
  `discover_builtin_tools()`, health tracking, check_fn gating.
- **Agents**: `agent/security_principal.py` — zero-trust principals
  (USER/AGENT/TOOL/MCP_SERVER/PLUGIN/SKILL/SESSION/WORKSPACE/DEVICE/SERVICE)
  + TrustLevel; `aetheros_swarm/registry.py` — 16-role capability registry;
  `aetheros_swarm/security.py` — ToolAuthorizer (least privilege,
  escalation denial, override-attempt scan, secret refusal).
- **Approvals/audit**: `aetheros_swarm/ops.py` — ApprovalQueue (fail-safe
  deny), AuditLog (JSONL), CheckpointStore, Tracer, EventStream.
  `aetheros_autonomy/service.py` — scoped expiring approvals, e-stop,
  safe mode. `cron/scheduler.py` — injection scanning for cron prompts.
- **Memory**: Master-41 `MemoryService` (scoped recall, provenance).
- **Desktop**: `app/extensions`, `app/marketplace`, `app/mcp-manager`,
  `app/skills`, `app/extension-sdk` views exist; IPC via `tui_gateway`
  `@method` pattern (tools/skills/memory2/swarm/automation precedents).
- **Crypto**: `cryptography==46.0.7` installed → real Ed25519/RSA
  signatures implementable. No new deps needed.

## Reusable components

skills_guard scanner, skills_hub sources, mcp_tool client, ToolRegistry,
security_principal principals, swarm ToolAuthorizer/ApprovalQueue/AuditLog,
MemoryService, IPC method pattern, desktop view/route/client pattern.

## Duplicated systems

Plugin dirs (`plugins/*`) have no unified manifest/lifecycle; skills, MCP,
tools each carry separate trust/install logic → unify under ONE registry,
ONE permission engine, ONE lifecycle (this phase).

## Missing pieces (built in `aetheros_extensions/`)

Canonical manifest, .aetherext package format, integrity/signature
verification, publisher trust + revocation, capability permission engine
with scopes, sandbox/capability host, extension lifecycle persistence,
dependency resolution, quarantine, update/rollback engine, static+dynamic
scanners for extensions, secret broker, ext-to-ext broker, sources
(remote/git/org/offline), CLI, IPC, Extensions Center UI.

## Security gaps closed here

Untrusted-by-default for all third-party code; runtime (not UI)
permission enforcement; MCP descriptions treated untrusted; no raw
Node/IPC/fs/shell/creds to extensions; scoped secrets only.

## Integration points

ToolRegistry (register ext tools w/ metadata), swarm AgentRegistry
(specialist agents), autonomy service (triggers/actions inherit autonomy),
MemoryService (scoped memory), MCP client (server lifecycle), gateway IPC,
desktop routes.

## Migration plan

Built-ins represented as BUILT_IN records (not fake installs); existing
SKILL.md dirs importable as skill extensions; MCP servers from config
adoptable as MCPExtensions; no existing behavior modified (additive).
