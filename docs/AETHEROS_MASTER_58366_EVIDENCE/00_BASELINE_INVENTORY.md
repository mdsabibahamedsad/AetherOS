# AETHEROS MASTER 58366 — Capability Inventory (2026-10-12)

Traced call paths only. No functionality inferred from names/buttons/docs.
Prior verified evidence reused (58361–58364); nothing re-audited without cause.
Live gateway/model/mic still unavailable — nothing below claims live verification.

| # | Capability | Class | Entry → implementation → tests |
|---|------------|-------|--------------------------------|
| 1 | Canonical request routing (Home/Chat/Jarvis → one runtime) | VERIFIED_IMPLEMENTED | Home `stashSessionDraft(null)` → chat `takeSessionDraft(null)` → `submitText`/`submitPromptText` → `prompt.submit`; Jarvis `submitJarvisCommand` → `executePipeline` → `session.create`+`prompt.submit`. Same gateway primitive everywhere |
| 2 | Model/provider registry | IMPLEMENTED_NOT_LIVE_VERIFIED | `providers/__init__` lazy discovery + `plugins/model-providers/*`; desktop `ModelsView` ← `getGlobalModelOptions`; local/cloud/auth分类 |
| 3 | Provider fallback chain | VERIFIED_IMPLEMENTED | `agent/agent_init.py:850-968` (`fallback_model` list/dict → `_fallback_chain`); `agent/orchestration/recovery.py` FALLBACK_MODEL strategy; ModelRouter (`aetheros_automation/routing/model_router.py`) |
| 4 | Tool registry + adapters | VERIFIED_IMPLEMENTED | `tools/registry.py` + `tools/*.py` auto-discovery; `toolsets.py` gating; `model_tools.py` dispatch; desktop tool cards render real events |
| 5 | MCP integrations | IMPLEMENTED_NOT_LIVE_VERIFIED | MCP catalog + desktop `mcp-manager` (persist/import/health-unknown); `mcp_*` results wrapped `<untrusted_tool_result>` (MASTER17 audit) |
| 6 | Multi-agent delegation | VERIFIED_IMPLEMENTED | `tools/delegate_tool.py` (leaf/orchestrator roles, depth/concurrency caps); desktop `$subagents` from `subagent.*` events |
| 7 | Task state machine | VERIFIED_IMPLEMENTED | Jarvis SUBMITTED→…→COMPLETED + FAILED/CANCELLED/TIMEOUT/UNAVAILABLE (`task-state-machine.test.ts`); chat `interrupted` flag; H-1 busy guard |
| 8 | Task persistence across restart | MISSING | Jarvis command log in-memory only; desktop action tasks TTL-pruned; cron jobs persist server-side (backend store) |
| 9 | Cancellation/recovery distinction | VERIFIED_IMPLEMENTED | `session.interrupt`, pipeline cancel flag, CANCELLED≠FAILED; 180s TIMEOUT; reload/edit resend |
| 10 | Memory + history + skills | IMPLEMENTED_NOT_LIVE_VERIFIED | `memory2.*` gateway methods + provider plugins; `SessionDB` FTS5; `skills/` + `optional-skills/` + curator lifecycle |
| 11 | Browser interaction | PARTIAL | Real `<webview>` paint + `browser_navigate` tool; desktop back/fwd/refresh partly local-only; AI assistant canned (documented 58362) |
| 12 | Filesystem ops | IMPLEMENTED_NOT_LIVE_VERIFIED | `readDesktopDir` bridge + Files view (loading/empty/error+Retry); Projects folder→workspace verified in code |
| 13 | Terminal workflows | IMPLEMENTED_NOT_LIVE_VERIFIED | Persistent PTY terminal + `terminal(background, notify)` gateway watcher |
| 14 | Jarvis voice (STT/TTS) | PARTIAL | Real `getUserMedia`/meter/providers; LISTENING⇔mic-live only; permission/error gates. Live audio unwitnessed (no mic session) |
| 15 | Automation/scheduling/jobs | IMPLEMENTED_NOT_LIVE_VERIFIED | `cron/jobs.py`+scheduler (3-min interrupt, locks, catchup); Automation Center `automation-*` client; Tasks lifecycle actions added this phase (H-2) |
| 16 | Permissions/approvals/policy/audit | VERIFIED_IMPLEMENTED | Jarvis `decideCapability` + `ApprovalRequiredError` both channels (tested); gateway approvals → Security Center `approval.respond`; prompt-injection scanners (cron/memory/browser/network) + `<untrusted_tool_result>` delimiters + redteam 0/12 escaped (prior reports) |
| 17 | Desktop shell (routes/palette/tasks/settings/diagnostics) | VERIFIED_IMPLEMENTED | 60+ routes wired; single palette + focus restore; Tasks (58362+this phase); settings search; diagnostics UI over simulated checks (documented limit) |
| 18 | Build/packaging/update/distribution | PARTIAL | Renderer `tsc -b`+`vite build` PASS (26s); updater + installer infra exist; fresh packaged build BLOCKED_EXTERNAL (no git provenance) |
| 19 | Task lifecycle controls in Tasks view | FIXED THIS PHASE (was PARTIAL) | Runtime had pause/resume/trigger/delete; UI exposed only view. Now wired + tested |

Notes: 58365 vision report ABSENT (prompts skipped 58365) — proceeded from 58363/58364. Web search unavailable this session (tool cancelled); competitive notes below are training-knowledge, labeled as such, and recommendations rest on repo gaps, not parity claims.
