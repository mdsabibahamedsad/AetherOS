# AETHEROS MASTER 44 — Extension Platform Report (evidence-backed)

## Executive Summary

Built the Universal Extension Platform (`aetheros_extensions/`, 13
modules) with real install/verify/authorize/execute/monitor/update/
disable/rollback/uninstall, plus CLI, agent tools, typed IPC, and
Extensions Center UI. No fake marketplace, installs, signatures,
sandbox, scans, or stats. Verdict: **PARTIALLY_CERTIFIED** (production
gates pass except cross-platform runtime validation, renderer/Electron
tests, and full-OS sandboxing, all marked BLOCKED with reasons).

## Repository Audit

`docs/AETHEROS_EXTENSION_PLATFORM_AUDIT.md`. Reused: skills_guard
scanner, skills_hub sources, mcp_tool client, ToolRegistry,
security_principal principals, swarm ToolAuthorizer/ApprovalQueue/
AuditLog, MemoryService, IPC `@method` pattern, desktop route/view/
client pattern. Unified previously separate skills/MCP/tools trust
paths under one registry/permission/lifecycle model. `cryptography`
46.0.7 present → real Ed25519 used, no new dependencies.

## Architecture / Lifecycle / Permissions / Security / Sandbox / Trust

See `docs/AETHEROS_EXTENSION_{PLATFORM,SECURITY,PERMISSION_MODEL,
MANIFEST,DEVELOPER_GUIDE,MCP_EXTENSION_MODEL,MARKETPLACE,THREAT_MODEL}.md`.
18-stage install flow with rollback; fail-closed validation; Ed25519
signatures with expiry/revocation; R0–R5 scoped grants with wildcard
deny-by-default; capability host (no Node/IPC/env/shell to extensions);
scoped SecretBroker; static PASS/WARN/BLOCK + isolated dynamic smoke
runs; quarantine; staged updates + auto-rollback; dep resolution with
cycle/confusion guards; compat engine; health/crash-loop tracking;
revoke-all enforced in runtime.

## Integrations (all real, tested)

MCP (adopt + health + description gate), skills (frontmatter parse,
untrusted flag), tools (registry with `ext:<id>` provider), agents
(swarm registry, same policy path), automation (autonomy caps, never
elevate L0), memory (scoped recall), sources (local/bundled/remote/
git/private/org + offline cache).

## Marketplace / Private / Developer / CLI / UI

Sources with trust policy; no fabricated stats (UI has no such fields);
org allow/block/sign/scan/pin policies; dev mode explicit + logged;
15 CLI commands proven live (package→validate→sign→trust→install→
enable→verify→uninstall with cleanup_verified); Extensions Center
(installed/detail/security/events) on live IPC; command palette not
extended (existing palette surfaces routes; NOT claimed).

## Testing

`tests/aetheros_extensions/test_extensions.py`: **39 passed**.
Gates: manifest (G3) ✓, permissions (G4) ✓, signatures (G5) ✓,
integrity (G6) ✓, deps (G7) ✓, MCP (G8) ✓, skills (G9) ✓, tools
(G10) ✓, agents (G11) ✓, automation (G12) ✓, memory (G13) ✓,
browser/computer perms (G14) ✓, quarantine (G15) ✓, rollback (G16) ✓,
adversarial A–Z subset (G17) ✓, IPC shape via method handlers (G18
partial — handler-level, no live renderer), renderer (G19) NOT RUN,
Electron (G20) NOT RUN, typecheck (G21) NOT RUN (no TS toolchain run),
lint (G22) ✓ ruff, perf (G23) ✓ measured, docs (G24) ✓, no-fake (G25)
✓.

Adjacent suites: toolsets 42 ✓, gateway server 258 ✓, model_tools 49 ✓,
registry+guard+mcp 309/311 (2 pre-existing env failures: cp1252
unicode test, ProgramFiles env test — files untouched by this phase).

## Adversarial results

11 malicious fixtures (env theft, exfil, shell, injection, traversal,
poisoned MCP text, tainted skill, dep cycle/confusion, tampered hash,
revoked key, corrupt update) — all blocked/flagged per policy; nothing
dangerous executed (static/validation level only).

## Performance (measured, `bench_results.json`)

Ed25519 sign+verify ×50: 0.01s. 10 exts: install 1.5s, activate 0.02s.
50 exts: install 8.0s, activate 0.3s. Permission eval ×1000: 0.002s.
Registry search ×100: ≤0.006s. 100 exts: NOT RUN (projected ~35s;
environment time box).

## Cross-platform

Windows RUNTIME_VALIDATED (all tests + CLI proven here). macOS/Linux:
SOURCE_SUPPORTED (pure-Python, no OS-specific code paths claimed),
BUILD/RUNTIME NOT VALIDATED. Sandbox PARTIAL all platforms (mechanism
table in code + docs); kernel isolation NOT IMPLEMENTED, never claimed.

## Files

Created: `aetheros_extensions/` (13 modules + bench_results.json),
`tools/extension_tool.py`, `aetheros_cli/extension_cmd.py`,
`tests/aetheros_extensions/test_extensions.py`,
`scripts/benchmark_extensions.py`,
`apps/desktop/src/app/extensions-center/index.tsx`,
`apps/desktop/src/lib/extension-client.ts`, 9 docs + this report.
Modified: `toolsets.py` (+extensions toolset), `tui_gateway/server.py`
(+12 methods), `aetheros_cli/main.py` (+extension parser),
`apps/desktop/.../routes.ts` + `desktop-controller.tsx` (+route/view).
Renamed: none. NOTE: tree contains extensive pre-existing
modifications from parallel work (rebrand, missions, etc.); claims
above cover only listed files (verified via targeted `git diff`).

## Known limitations / Blockers / Residual risks

BLOCKED: renderer/Electron/typecheck runs; 100-ext scale run; kernel
sandbox; distributed multi-device locks; native service claims (none
made). Residual: in-process Python entrypoints (PARTIAL sandbox);
stolen-key window before revocation; availability of remote registries.
`extension update --source` CLI semantics per-id (documented in help).

## Certification matrix

25 gates: 20 PASS, 4 NOT RUN (G18 partial, G19, G20, G21), 1 PARTIAL
(G23 scale capped at 50). No gate FAILED. **PARTIALLY_CERTIFIED.**
