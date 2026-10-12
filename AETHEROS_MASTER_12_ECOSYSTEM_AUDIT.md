# AETHEROS MASTER 12 — UNIVERSAL CAPABILITY ECOSYSTEM AUDIT (PHASE 0)

**Status:** Audit complete. No production code modified.
**Method:** Four parallel subsystem sweeps (tools, skills, security/config,
plugins+MCP) plus direct verification of registry metadata usage, MCP protocol
handling, extension-package wiring, and plugin/marketplace surfaces.
**Scope note:** Findings below are grounded in file paths + line references.
Where a capability exists but is *latent* or *orphaned*, that is stated
explicitly — it changes the implementation strategy (wire-in vs build-new).

---

## EXECUTIVE SUMMARY

AetherOS already ships ~80% of Master 12's functional surface, but it is
distributed across **four parallel capability systems** that do not share a
common model:

| # | System | Entry points | State |
|---|--------|--------------|-------|
| A | Core tools | `tools/registry.py` → `model_tools.py` → `toolsets.py` | Production runtime |
| B | Skills | `agent/skill_utils.py`, `tools/skills_hub.py`, `tools/skills_guard.py`, `agent/curator.py` | Production, hardened |
| C | Plugins | `aetheros_cli/plugins.py`, `plugins/`, `plugin_permissions.py`, `marketplace_manager.py` | Production |
| D | MCP client/servers | `tools/mcp_tool.py` (+ `mcp_oauth*.py`), `aetheros_cli/mcp_catalog.py`, `mcp_manager.py` | Production |

Plus a fifth, **disconnected layer**: the `extensions/` package
(`Capability`, `CapabilityRegistry`, `ExtensionManager`, sandbox, policy
engine, event bus) which implements a universal capability model — but is
consumed only by the SDK tier (`sdk/permissions.py`,
`aetheros_cli/sdk_commands.py`, `aetheros_developer_platform/`,
`aetheros_production/`) and **never by the agent core**
(`run_agent.py`, `cli.py`, `gateway/`, `model_tools.py`).

Critical single findings:

1. **Risk metadata is dead code.** `tools/registry.py:99-109` accepts
   `risk_level / permissions / confirmation_required / sandbox_config /
   retry_config / circuit_breaker_config / timeout_config /
   output_security_level / version`, but `register()` hardcodes defaults
   (`:368-376`) and only `get_tool_info()` (`:591-626`) ever reads them.
2. **The security PEP is latent.** `ToolAuthorizationService.check()` wraps
   every dispatch (`model_tools.py:1140-1210`, fail-closed), but the
   SecurityContext principal/token is only set inside an except-fallback
   branch of `agent/agent_init.py:1036` — so authorization effectively never
   activates in normal operation.
3. **At least six distinct risk taxonomies** coexist (§11): dead registry
   fields, `aetheros_actions.RiskLevel`, `agent/authorization_engine.RiskLevel`,
   `agent/continuous_authorization` levels, `aetheros_security.permissions`,
   and `security.control_plane.action_guard` R1–R4 tiers.
4. **MCP is mature**: stdio + Streamable HTTP + SSE transports, protocol
   version negotiation with fallback `"2026-07-28"`, capability-aware
   resources/prompts, OAuth, TLS options, timeouts. Missing: Tasks/long-running
   ops, Apps/UI extensions, extension metadata tracking.
5. **Skills are hardened** (quarantine→scan→confirm→lock pipeline, trust
   tiers, curator lifecycle) but have no semver compatibility checks and no
   inter-skill conflict detection.

---

## 1. EXISTING TOOLS

- **Registration:** `tools/registry.py:292-313` —
  `register(name, toolset, schema, handler, check_fn=None, requires_env=None,
  is_async=False, max_result_size_chars=None, dynamic_schema_overrides=None,
  override=False, provider="aetheros", platform=None,
  supports_streaming/cancellation/background_execution=False,
  output_schema=None)`.
- **Shadow protection:** cross-toolset re-registration rejected unless
  `override=True`; MCP→MCP overwrite allowed (`:322-354`).
- **Discovery:** `discover_builtin_tools()` AST-scans `tools/*.py` for
  top-level `registry.register(...)` calls, then imports (`:57-74`). Import
  failures logged + skipped.
- **Availability:** per-tool `check_fn` with 30s TTL cache (`:184-199`);
  first check registered in a toolset becomes the toolset gate (`:385-386`).
- **Execution:** `model_tools.handle_function_call()` (`:887-1285`) —
  coerce args → Tool Search bridge → middleware → agent-loop stubs
  (todo/memory/session_search/delegate_task) → plugin `pre_tool_call` →
  ACP edit approval → observability → **ToolAuthorizationService.check()**
  (fail-closed, latent) → dispatch → `post_tool_call` →
  `transform_tool_result`. Errors sanitized (`_sanitize_tool_error`, 2000-char
  cap).
- **Async bridge:** `_run_async()` persistent main loop + worker loops;
  300s hard timeout when called inside a running loop (`:95-184`).
- **Toolsets:** `toolsets.py` `TOOLSETS` dict; `_HERMES_CORE_TOOLS` ≈50
  tools; `_AETHEROS_WEBHOOK_SAFE_TOOLS` constrained set; per-platform
  `aetheros-<platform>` sets; composite `aetheros-gateway`;
  `resolve_toolset()` recursive with cycle/diamond handling.
  `toolset_distributions.py` is RL/data-gen only.
- **Inventory:** 86 modules under `tools/` — terminal/process
  (`terminal_tool.py`, `process_registry.py`, `read_terminal_tool.py`),
  file (`file_tools.py`: read/write/patch/search), web/browser
  (`web_tools.py`, `browser_tool.py` ×10 regs, `browser_cdp_tool.py`,
  `browser_camofox.py`), vision/media (`vision_tools.py`, image/video gen,
  tts/transcription), agent infra (`delegate_tool.py`, `todo_tool.py`,
  `memory_tool.py`, `session_search_tool.py`, `clarify_tool.py`,
  `checkpoint_manager.py`, `blueprints.py`), skills family (9 modules),
  messaging/platforms (`send_message_tool.py`, `discord_tool.py`,
  `feishu_doc/drive`, `homeassistant_tool.py`, `yuanbao_tools.py`,
  `integration_tools.py`), scheduling/board (`cronjob_tools.py`,
  `kanban_tools.py`), security plumbing (`approval.py`, `url_safety.py`,
  `path_security.py`, `website_policy.py`, `tirith_security.py`,
  `threat_patterns.py`, `osv_check.py`, `credential_files.py`,
  `env_passthrough.py`, `write_approval.py`), output governance
  (`tool_output_limits.py`, `tool_result_storage.py`, `budget_config.py`,
  `ansi_strip.py`, `schema_sanitizer.py`, `tool_search.py`).
- **Environments:** `tools/environments/` — local (spawn-per-call bash, no
  isolation), docker, singularity, modal (+managed_modal), daytona, ssh,
  file_sync; unified spawn-per-call base.
- **Health:** success/failure counters + health transitions tracked inline in
  `dispatch()` (`:504-541`); health text injected into schema descriptions
  (`:466-476`).

## 2. EXISTING SKILLS

- **Trees:** `skills/` — 18 categories, ~73 SKILL.md (bundled, active);
  `optional-skills/` — 18 categories, ~98 SKILL.md (install-gated).
- **Parser:** `agent/skill_utils.py` `parse_frontmatter()` (CSafeLoader);
  consumed fields: `name`, `description`, `platforms`, `environments`
  (kanban/docker/s6 gates), `metadata.aetheros.{tags, related_skills, config,
  requires_tools, requires_toolsets, fallback_for_tools,
  fallback_for_toolsets, blueprint}`, `prerequisites.*` (legacy),
  `setup.*`, `required_environment_variables`,
  `required_credential_files`, `compatibility` (echoed only).
  **NOT parsed:** `version`, `author`, `license`.
- **Activation:** always-on compact index in system prompt
  (`agent/prompt_builder.build_skills_system_prompt`, two-layer cache +
  disk snapshot); model-driven progressive disclosure via
  `skills_list`/`skill_view` (tiers 1–3: metadata → SKILL.md →
  references/templates/scripts). Slash commands inject skill content as a
  **user message** (cache-safe). `--skills a,b,c` preload. Token levers:
  60-char description cap, coding-posture `compact_categories`.
- **Hub:** `tools/skills_hub.py` — `SkillSource` ABC with 10 adapters
  (OptionalSkillSource builtin-trust, AetherosIndex JSON catalog 6h TTL,
  SkillsSh sitemap, WellKnown, Url, GitHub taps w/ trusted repos, ClawHub
  community, ClaudeMarketplace, LobeHub, BrowseSh). State at
  `~/.aetheros/skills/.hub/`: `quarantine/`, `lock.json` (source,
  identifier, trust_level, scan_verdict, sha256, validated files),
  `audit.log`, `taps.json`.
- **Install pipeline:** resolve → fetch → quarantine → `scan_skill()` →
  policy check → user confirm → install from quarantine → lock record +
  audit log → prompt-cache invalidation. Guards: path traversal/junction/
  symlink rejection, ZIP-member validation, SSRF-guarded HTTP.
- **CLI:** `aetheros skills browse|search|install|inspect|list|check|update|
  audit|uninstall|reset|opt-out|opt-in|publish|snapshot|tap`; bundled sync
  engine `tools/skills_sync.py` (`.bundled_manifest` hashes).
- **Scanning:** `tools/skills_guard.py` ~100 threat patterns (exfiltration,
  injection, destructive, persistence, network, obfuscation, supply-chain,
  crypto-mining, secrets) + invisible-unicode + structural checks +
  `.skillignore`; trust matrix (builtin=allow-all, trusted=dangerous blocked,
  community=any finding blocks unless `--force`, dangerous never forceable).
  Opt-in AST deep scan `tools/skills_ast_audit.py`. Injection-pattern warn at
  view time (`tools/skills_tool.py`). Agent-created skill scanning gated by
  `skills.guard_agent_created` (**default off**).
- **Curator:** `agent/curator.py` + `agent/curator_backup.py` +
  `tools/skill_usage.py` (sidecar `.usage.json`) — states active→stale→
  archived; `pinned` exempts from all transitions + LLM review;
  provenance restriction `created_by == "agent"`; hub-installed skills
  never eligible; tar.gz pre-run backups with undoable rollback; CLI
  `aetheros_cli/curator.py` verbs status|run|pause|resume|pin|unpin|
  archive|restore|prune|backup|rollback.

## 3. EXISTING PLUGINS

- **Loader:** `aetheros_cli/plugins.py` (1959 LOC) — four discovery sources:
  bundled `<repo>/plugins/<name>/` (memory/ + context_engine/ excluded),
  user `~/.aetheros/plugins/`, project `./.aetheros/plugins/`
  (opt-in via env flag), pip entry-point group `aetheros_agent.plugins`.
  Later sources override earlier on collision. Requires `plugin.yaml`
  manifest + `__init__.py::register(ctx)`.
- **Hook surface (`VALID_HOOKS`):** `pre_tool_call`, `post_tool_call`,
  `transform_terminal_output`, `transform_tool_result`,
  `transform_llm_output`, `pre_llm_call`, `post_llm_call`,
  `pre_api_request`, `post_api_request`, plus observer-middleware registry
  (`aetheros_cli/middleware.py`).
- **ctx API:** `ctx.register_tool()` delegates to `tools.registry.register()`
  (so plugin tools land in the same registry as core tools);
  `ctx.register_cli_command()` wires argparse subtrees into `aetheros`.
- **Tree inventory:** `plugins/memory/` (honcho, mem0, supermemory, byterover,
  hindsight, holographic, openviking, retaindb), `plugins/context_engine/`,
  `plugins/model-providers/` (zai, xiaomi, …), `plugins/kanban/`
  (dashboard + systemd unit), `plugins/web/xai/`, `plugins/browser/firecrawl/`,
  `plugins/image_gen/xai/`, `plugins/observability/nemo_relay/`,
  `plugins/platforms/teams/`, `plugins/dashboard_auth/self_hosted/`,
  `plugins/security-guidance/`, `plugins/aetheros-achievements/`,
  `plugins/disk-cleanup/`, `plugins/google_meet/`, `plugins/web/`.
- **Permissions:** `aetheros_cli/plugin_permissions.py` (669 LOC) —
  `PermissionMode` allow/deny/ask over ~20 categories × resources incl.
  `mcp.connect/invoke/list`, `filesystem.read/write/delete/execute`,
  `secrets.read/write`, `network.connect/listen/dns`.
- **Marketplace:** `aetheros_cli/marketplace_manager.py` (833 LOC) —
  catalog management, install/update/remove, `PluginVersion(version,
  changelog, published, checksum)`, dependency resolution, permission
  declarations.
- **SDK tier:** `aetheros_cli/extension_sdk.py` templates (incl.
  `mcp_server`), `aetheros_cli/sdk_commands.py` wiring
  `get_extension_manager()` into `aetheros sdk` verbs; `PLUGIN_SDK.md` docs.
- **Specialized plugin families** (separate ABCs/orchestrators):
  memory providers (`agent/memory_provider.py` ABC + `agent/memory_manager.py`),
  model providers (`plugins/model-providers/` lazy discovery
  bundled→user→legacy `providers/<name>.py`, last-writer-wins),
  context engines (`agent/context_engine.py`),
  image-gen providers (`agent/image_gen_provider.py`),
  gateway hooks (`gateway/builtin_hooks/`).

## 4. EXISTING MCP SYSTEMS

- **Client:** `tools/mcp_tool.py` (~3k LOC).
  - Transports: **stdio**, **Streamable HTTP**, **SSE**
    (`sse_client`, `sse_read_timeout=300s`) — `:188-207`, `:1693-1825`.
  - Protocol version: `LATEST_PROTOCOL_VERSION` from SDK with fallback
    `"2026-07-28"` (`:179-203`); server's negotiated `protocolVersion`
    recorded (`:1528`); `mcp-protocol-version` header on HTTP (`:1667`).
  - Capability-aware: uses server-advertised `.capabilities.resources` /
    `.capabilities.prompts` instead of assuming (`:1197-98`); skips
    `tools/list` when connection kept alive for prompts/resources (`:1846+`).
  - Resources: `resources/list` + `resources/read` handlers
    (`:2897-2999`). Prompts: `prompts/list` + `prompts/get` (`:3015-3128`).
    `list_changed` notifications observed-but-ignored (`:1299-1301`).
  - Auth: OAuth passthrough into SSE/streamable clients (`_oauth_auth`,
    `:1720`); TLS verify/cert kwargs; content-type pre-flight probe on
    Streamable HTTP (`:1908`). Token managers: `tools/mcp_oauth.py`,
    `tools/mcp_oauth_manager.py`.
  - Timeouts: `tool_timeout` default 60s wired into handler factories.
- **Exposure:** MCP tools register into `tools/registry.py` as normal tools;
  registry shadow rules permit MCP→MCP overwrite only (`:327-331`).
- **Configuration:** `config.yaml` top-level `mcp:` section
  (`config.py:1297`) + `mcp_servers` dict consumed across
  `aetheros_cli/mcp_config.py` (add/remove/get), `mcp_picker.py` (curses UI),
  `mcp_startup.py` (auto-start), `initialization_flow.py` (setup wizard step),
  `commands.py` `/mcp`, `subcommands/mcp.py`, `web_server.py` REST +
  background `mcp-install` actions.
- **Catalog/installer:** `aetheros_cli/mcp_catalog.py` — installs into
  `~/.aetheros/mcp-installs/`, writes `cfg["mcp_servers"]` entries.
  `optional-mcps/` dir at repo root. Docs: `MCP_GUIDE.md`.
- **Server mode:** `mcp_serve.py` exposes AetherOS itself as an MCP server
  (`aetheros mcp serve`).
- **Security scanning:** `aetheros_cli/security_audit.py` attributes tool
  surface to sources like `"mcp:<server_name>"`.

## 5. EXISTING REGISTRIES

1. `tools/registry.py` — production model-tool registry (schemas, handlers,
   check_fn gating, health counters). **Canonical.**
2. `extensions/registry.py` `CapabilityRegistry` — SDK-tier capability
   registry (see §D above); not consulted by the agent core.
3. `marketplace_manager.py` internal catalog (versions, checksums,
   permissions) for plugins.
4. `aetheros_cli/mcp_catalog.py` — curated MCP server catalog + installer.
5. `tools/skills_hub.py` hub state (lock.json + sources + taps) for skills.
6. Provider registries: `plugins/model-providers/` lazy discovery
   (`providers/__init__.py`), memory-provider orchestration.

## 6. EXISTING LOADERS

- Tool loader: AST-scan import (`tools/registry.py:57-74`).
- Plugin loader: manifest + module load (`aetheros_cli/plugins.py`).
- Extension loader: disk / URL / package (`extensions/loader.py`,
  `LoaderResult`) — SDK tier only.
- Skill loader: frontmatter parse + index builder + progressive disclosure
  (`agent/skill_utils.py`, `agent/prompt_builder.py`, `tools/skills_tool.py`).
- MCP connector loader: per-server session manager in `tools/mcp_tool.py`
  (stdio subprocess / HTTP session), auto-start via `mcp_startup.py`.
- Model-provider loader: lazy scan of three roots with user override.

## 7. EXISTING PERMISSIONS

- **Terminal/command approvals:** `tools/approval.py` (1793 LOC) —
  HARDLINE_PATTERNS (unconditional block), ~60 DANGEROUS_PATTERNS
  (rm -r, mkfs/dd, SQL DROP, sudo gating, sed -i on .env/config,
  git reset --hard/force-push, curl|sh, heredoc exec…); YOLO frozen at
  import (injection-resistant); persistent `command_allowlist`;
  auxiliary-LLM smart review (`APPROVE/DENY/ESCALATE`); gateway async
  decisions + per-platform resolution; container backends skip approvals
  (isolation substitutes); subagents auto-deny when
  `delegation.subagent_auto_approve=False`.
- **Edit approvals:** ACP adapter `edit_approval.py` for write_file/patch;
  SENSITIVE_AUTO_APPROVE_NAMES (.env, id_rsa) always gated.
- **Plugin permissions:** `plugin_permissions.py` rules (allow/deny/ask ×
  resource strings).
- **Security control plane (config):** `security.control_plane.` —
  `tool_authorization`, `data_flow_guard`, `action_guard` (R3/R4 risk tiers,
  bulk_threshold), `budgets`, six kill switches (CLI:
  `aetheros platform security kill-switch`).
- **Latent enforcement:** `ToolAuthorizationService.check()` around every
  dispatch (see Executive Summary #2).
- **UI surfaces:** TUI JSON-RPC approval/sudo/clarify request/respond;
  curses `tools_config.py`; web dashboard endpoints.

## 8. EXISTING CREDENTIAL HANDLING

- Primary store `~/.aetheros/.env` — atomic tmp+replace writes, mode
  preserved or 0600, denylisted-var rejection, ASCII enforcement
  (`aetheros_cli/config.py` get_env_value/save_env_value).
- OAuth/provider state `auth.json` — O_EXCL 0600, parent 0700,
  profile-fallback (`aetheros_cli/auth.py`).
- OS keychain opt-in: `security.api_key_storage = env|keychain|auto`
  → `aetheros_cli/api_key_store.py` → `aetheros_security/secrets/`
  (Windows CredMan via ctypes, macOS Keychain, Linux Secret Service,
  encrypted vault fallback).
- Bitwarden Secrets Manager integration (opt-in, `secrets.bitwarden`).
- Redaction: `RedactingFormatter` (`agent/redact.py`) wraps ALL log handlers
  (`aetheros_logging.py`) masking API keys, JWTs, private keys, tokens,
  DB connstrs, phone numbers; separate observability redaction.
- Secret capture UI never echoes values to the model
  (`aetheros_cli/callbacks.prompt_for_secret`); skills declare
  `required_credential_files` resolved at execution time.
- Env passthrough control for sandboxes: `tools/env_passthrough.py`;
  Windows essential-env allowlist in `code_execution_tool.py:110`.

## 9. EXISTING EXTENSION APIs

- Plugin hooks (§3) invoked from `model_tools.py` (pre/post tool) and
  `run_agent.py` (lifecycle).
- `ctx.register_tool` / `ctx.register_cli_command` (plugin context).
- Middleware seam: `transform_tool_result` first-string-wins
  (`model_tools.py:1254-1278`); observer middleware schema-versioned.
- Extensions package API (SDK tier): `ExtensionManager`, `load_extension`,
  `ExtensionSandbox(SandboxConfig, SandboxMode)`, `PolicyEngine`,
  event bus — exported from `extensions/__init__.py`.
- Gateway hook point: `gateway/builtin_hooks/` (always-registered, none ship).
- MCP server mode: `mcp_serve.py`.
- ACP adapter (`acp_adapter/`) exposes the agent to editors.

## 10. EXISTING CONFIGURATION FORMATS

- `DEFAULT_CONFIG` v29 (`aetheros_cli/config.py:2723`), ~75 top-level
  sections incl.: `toolsets`, `tools.<platform>.enabled/disabled`,
  `approvals` (mode=manual, timeout=60, cron_mode=deny,
  mcp_reload_confirm, destructive_slash_confirm), `command_allowlist`,
  `security` (redact_secrets, tirith_*, website_blocklist.domains,
  acked_advisories, allow_lazy_installs, api_key_storage, control_plane),
  `network`, `skills` (+ guard flags), `curator`, `delegation`,
  `code_execution`, `gateway`, `mcp`, `plugins`, `hooks`,
  `hooks_auto_accept`, `privacy`, `observability`, `logging`.
- Three loaders (per AGENTS.md): `load_cli_config()` (CLI),
  `load_config()` (`aetheros tools`/subcommands), raw YAML (gateway).
  Migration ladder v3→v29 with sanitize/validate helpers.
- `.env` = secrets only (~130 documented OPTIONAL_ENV_VARS entries with
  category/password metadata).
- Manifests: `plugin.yaml` (general plugins), `SKILL.md` frontmatter
  (skills), `mcp_servers` config entries (MCP), extension manifests
  (`extensions/loader.py`), marketplace records.

## 11. EXISTING DUPLICATION

1. **Registries ×5** — tools/registry vs extensions/CapabilityRegistry vs
   marketplace catalog vs mcp_catalog vs skills-hub state.
2. **Permission models ×5** — plugin_permissions rules,
   marketplace Permission enum, approval.py pattern engine,
   `aetheros_security/permissions` (PermissionRequest/RiskLevel),
   `control_plane.action_guard` tiers.
3. **Risk taxonomies ×6** — dead `ToolEntry.risk_level`,
   `aetheros_actions.RiskLevel` (LOW..CRITICAL + AutonomyLevel),
   `agent/authorization_engine.RiskLevel` (NONE..CRITICAL + policy
   conditions), `agent/continuous_authorization` string levels,
   jarvis `permissions.risk_level()`, action_guard R1–R4.
4. **Extension packaging ×3(+)** — general plugins (plugin.yaml),
   extensions-package manifests, extension_sdk templates — plus SKILL.md
   and mcp_servers entries as de-facto formats.
5. **Installers ×3** — skills hub pipeline, marketplace manager,
   mcp catalog installer (each with its own trust/quarantine semantics).
6. **Config loaders ×3** (documented AGENTS.md pitfall).

## 12. MISSING FUNCTIONALITY (phase-by-phase coverage)

Legend: ✅ exists · 🟡 partial/latent · ❌ absent.

| Phases | Topic | Status | Notes |
|---|---|---|---|
| 0 | Ecosystem audit | ✅ | This document |
| 1–2 | Universal capability model + registry | 🟡 | `extensions/capability.py` model exists but narrow (14 caps) & disconnected from runtime; production registry is `tools/registry.py`. Need adapters/facade — NOT a new registry (rule #2) |
| 3 | Namespacing | 🟡 | `provider=` field, `plugin:skill` qualified names, `mcp:<server>` attribution exist; no unified stable-ID scheme (`aetheros.tool.filesystem` style) or alias migration map |
| 4–5 | Discovery + search | 🟡 | Per-family discovery/search exist (AST scan, hub sources, 4-source plugin scan, mcp_servers+catalog, fuzzy_match); no unified facade |
| 6 | Capability matching | 🟡 | Toolset resolution + delegation + auxiliary routing; no requirement-driven selection across families |
| 7 | Tool contracts | 🟡 | input schema + `output_schema` supported; side-effects/errors/risk not modeled (dead fields) |
| 8 | Input validation | 🟡 | type coercion robust; `registry.validate_tool_schema()` has zero callers |
| 9 | Output validation | ✅ | max_result_size_chars, tool_output_limits, result storage spill, ansi_strip, error sanitize; content-type checks on MCP HTTP probe |
| 10–11 | Risk classification + annotations | ❌/🟡 | classification absent as live concept; streaming/cancellation/background flags exist; read-only/destructive annotations inferred only via command regexes |
| 12, 15, 32 | Permission engine, execution gate, boundary | 🟡 | handle_function_call IS the gate with correct ordering; policy evaluation latent (activate = small change, big win) |
| 13 | Least privilege | 🟡 | check_fn gating, scoped token locks, credential_files, webhook-safe toolset; no per-resource scopes |
| 14 | Sandboxing | ✅/🟡 | environments backends mature; extensions/sandbox unused by core |
| 16 | Timeouts/cancellation | ✅ | _run_async 300s, MCP tool_timeout, process_registry, interrupt machinery |
| 17 | Retry policy | 🟡 | per-tool only (terminal); correct that there's no blind generic retry |
| 18 | Idempotency keys | ❌ | absent generally |
| 19–20 | Health + checks | ✅ | counters + transitions inline; check_fn TTL; no aggregate health surface beyond tools_config UI |
| 21–25 | MCP client/transports/tools | ✅ | see §4 |
| 26 | MCP resources bounded | 🟡 | handlers exist; verify size limits/read bounding during impl |
| 27 | MCP prompts | ✅ | list/get handlers, distinct semantics preserved |
| 28 | MCP tasks/long-running | ❌ | add behind negotiated-capability detection |
| 29 | MCP extensions tracking | ❌ | absent |
| 30 | MCP Apps/UI | ❌ | absent (needs CSP/origin/isolation design) |
| 31, 34, 36 | MCP auth / injection / rotation | 🟡 | OAuth + TLS present; verify token logging hygiene + refresh paths during impl |
| 33, 35 | Credential mgmt/scoping | ✅ | §8 strong; profile/project/user scoping present |
| 37 | Plugin manifest normalization | 🟡 | plugin.yaml lacks health_check/upgrade_policy/rich permissions linkage to plugin_permissions |
| 38–39 | Install pipeline + trust | ✅/🟡 | skills exemplary; plugins marketplace partial; MCP catalog installer simpler |
| 40 | Plugin sandbox | 🟡 | process-level isolation weak; extensions/sandbox dormant |
| 41–44 | Lifecycle/deps/versioning/rollback | 🟡 | skills complete (curator backups); plugins partial (marketplace claims update/remove); semver compat checks absent everywhere |
| 45 | Schema-driven config validation | 🟡 | deep-merge + validate_config_structure; no per-plugin config_schema enforcement |
| 46–48, 50–51 | Skill registry/activation/composition/isolation/versioning | ✅/🟡 | strong; composition=bundles only; min-version compat ❌ |
| 49 | Skill conflict detection | ❌ | only requires_tools/toolsets declared, no conflict resolver |
| 52 | Skill scanning | ✅ | guard + AST audit; honest "hints not verdicts" posture |
| 53 | Remote capability safety | 🟡 | SSRF guards/TLS/timeouts; rate limiting absent |
| 54 | Network policy (egress allowlist) | 🟡 | website_blocklist + url_safety; NetworkSecurityManager orphaned; no domain allowlist enforcement for arbitrary tools |
| 55–56 | Data-flow control/classification | 🟡 | DataFlowGuard + classification modules exist, orphaned |
| 57 | User consent UX | 🟡 | approval prompts + confirm flows; no data-preview consent for external sends |
| 58–60 | Tool/capability/permission UI | 🟡 | curses tools_config + web dashboard + TUI prompts; no unified capability detail page (risk/provider/health) |
| 61–63 | Marketplace architecture/trust abstraction | 🟡 | marketplace_manager + hub sources + mcp catalog; trust policies ad hoc per family |
| 64–65 | Package integrity/supply chain | ✅ | sha256 lock records, checksums, dep pinning policy (AGENTS.md), osv_check |
| 66–68 | Malicious-extension/injection defense | ✅/🟡 | guard patterns + tirith + cron assembled-prompt scanner + error sanitization; tool-output-as-data separation partial (no structured untrust marking) |
| 69 | MCP server isolation (min context) | 🟡 | per-server sessions; context minimization not explicit |
| 70–73 | Composition/auto-routing/fallback/recovery | 🟡 | delegation+bundles+fallback providers; no cross-family router; health recovery = curator only for skills |
| 74–75 | Observability/audit | ✅ | redacted logs, trajectories, hub audit.log, session DB, approval events; protect-at-rest hardening open |
| 76 | Telemetry controls | ✅ | opt-in posture documented (AGENTS.md policy) |
| 77–78 | Offline/local-first | 🟡 | local backends + index-cache TTLs; no degraded-mode labeling |
| 79–85 | Cloud/project/user/system scoping, migration, removal, ownership | ✅/🟡 | profiles + project/user plugin dirs + migrations v3→29; uninstall preserves-user-data rules implicit |
| 86–91 | Connector classes | ✅ | API (web/integration/HA), CLI (terminal), DB (via terminal/code_execution), filesystem (file_tools+path_security), browser/computer-use tools |
| 92–95 | Test harnesses | 🟡 | huge suite + hub tests; no generic extension harness; MCP compat tests unknown |
| 96–98 | Regression/perf/cross-platform | 🟡 | run_tests.sh CI parity; perf benches absent |
| 99 | Final audit | ⬜ | after implementation |

## 13. COMPATIBILITY RISKS

1. **Prompt-cache invariants:** anything that mutates tool schemas
   mid-conversation breaks caching. Note `get_definitions()` already injects
   health text into descriptions (`tools/registry.py:466-476`) — any new
   capability-metadata surface must stay byte-stable per conversation.
2. **Dead-code resurrection hazard** (documented repo pattern): activating
   `ToolEntry` pipeline fields or `validate_tool_schema()` must be E2E-proven,
   not just wired.
3. **Three config loaders** — new capability config must land in
   `DEFAULT_CONFIG` AND reach gateway raw-YAML readers.
4. **Shadow-registration semantics:** plugins rely on `override=True`
   behavior and MCP overwrite rules; namespacing must not change existing
   registration identity matching.
5. **Skill slash commands are user-message injections**; changing loading
   order or activation risks both caching and alternation invariants.
6. **Windows-first environment here:** POSIX-only primitives in new code will
   break local runs; follow platforms-gating standards.
7. **Packaged desktop copies** (`apps/desktop/dist-packaged/**`) duplicate
   backend modules — they lag `main`; do not treat them as source of truth.

## 14. SECURITY RISKS

1. Latent authorization service (Executive Summary #2) — enforcement exists
   but principal provisioning doesn't; either activate deliberately or the
   control_plane config promises something it can't enforce.
2. Six divergent risk taxonomies — inconsistent policy decisions across
   layers; consolidation needed before adding a seventh anywhere.
3. `guard_agent_created` default OFF — agent-authored skills unscanned
   unless opted in.
4. Orphaned security modules (`NetworkSecurityManager`, `DataFlowGuard`,
   `security_integration` CLI, `web_security_api` routes) create false
   confidence if referenced by docs/UI.
5. MCP `list_changed` notifications ignored — stale tool/resource views
   until reconnect.
6. No egress allowlisting for arbitrary tools/plugins; website_blocklist
   covers browser/web-fetch only.
7. Tirith fail_open=True default — scanner failure silently disables
   pre-exec screening.
8. Secrets hygiene is strong (redaction, atomic 0600 writes, keychain) but
   MCP token-at-rest format and refresh handling need verification before
   claiming Phase 31/36 compliance.

## 15. FILES THAT MUST REMAIN UNTOUCHED

Core narrow-waist + preservation rule (AGENTS.md rubric):

- `run_agent.py`, `cli.py`, `gateway/run.py` — no plugin-driven edits; any
  touch must preserve caching/alternation/system-prompt stability.
- `tools/registry.py` public `register()` signature (additive-only if ever).
- `toolsets.py` existing set membership/order (cache-stable IDs).
- `aetheros_cli/plugins.py` discovery contract + hook names.
- `tools/approval.py` pattern tables (HARDLINE/DANGEROUS) — additive only.
- `agent/skill_utils.py` parser outputs consumed elsewhere.
- All working platform adapters, `aetheros_state.py`, cron/kanban cores,
  memory/model-provider plugin ABCs, `ui-tui/` + `tui_gateway/` protocols,
  `acp_adapter/`, packaged `apps/desktop/dist-packaged/**`.
- User data/state layouts: `~/.aetheros/*` (profiles, skills/.hub,
  mcp-installs, sessions).

## 16. FILES THAT REQUIRE MODIFICATION (implementation targets)

Anticipated (to be confirmed per-phase, smallest-diff first):

| Target | Why |
|---|---|
| `tools/registry.py` | Activate risk/annotation metadata (populate + consume), optional stable-ID getter |
| `model_tools.py` | Gate-stage wiring: schema validation call site, policy-check activation switch, idempotency hook point |
| `agent/agent_init.py` | Fix SecurityContext provisioning path (move out of except-fallback) |
| `aetheros_cli/security_integration.py`, `web_server.py` | Mount orphaned security CLI/API (behind config gates) |
| `extensions/capability.py`, `extensions/registry.py` | Normalize to Master 12 capability record; adapters FROM tools/skills/plugins/MCP |
| `tools/mcp_tool.py` | Tasks support behind negotiation; extension metadata; resource read bounding; refresh handling |
| `tools/skills_hub.py` + `agent/skill_utils.py` | Parse version/compatibility frontmatter; conflict declaration field |
| `aetheros_cli/plugin_permissions.py` + `marketplace_manager.py` | Link permission model into ctx + manifest schema |
| `aetheros_cli/config.py` | New DEFAULT_CONFIG keys (capability facade, network policy, telemetry labels) + version bump ONLY if migration needed |
| `tests/` | New harnesses per Phases 92–95 following repo standards |

---

## RECOMMENDED STRATEGY (post-audit)

Footprint-ladder compliant (reuse > extend > new):

1. **Wire, don't rebuild:** activate the existing execution-gate pieces
   (schema validation, latent authz) behind `security.control_plane` gates
   already present in config.
2. **Adapt, don't duplicate:** make `extensions/` the capability *facade*
   with read-only adapters projecting tools/skills/plugins/MCP into one
   queryable view; keep `tools/registry.py` canonical for execution.
3. **Consolidate risk taxonomy once:** pick `aetheros_security` RiskLevel as
   the enum; map others to it at boundaries; delete dead registry defaults.
4. **MCP gaps last and gated:** Tasks/extensions/Apps only behind
   negotiated-capability detection (server may not support them).
5. Every change: regression via `scripts/run_tests.sh` before/after;
   E2E against temp `AETHEROS_HOME`; no mid-conversation schema mutation.

## OPEN DECISIONS (require owner sign-off before Phase 1)

1. Activate latent `ToolAuthorizationService` (behavior change for sessions
   that previously skipped authz) — default on/off?
2. Single risk taxonomy adoption + whether `action_guard` tiers become the
   user-facing knob.
3. Namespacing scheme rollout: alias-map only (zero breakage) vs re-ID with
   migration.
4. Scope cut for this pass: recommended Phase order 1–20, 46–57, 74–78 now;
   MCP Tasks (28), Apps (30), UI pages (58–60) as follow-ups.
