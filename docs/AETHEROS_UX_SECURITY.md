# AetherOS UX Security

How the Master 63 UX work preserves the desktop security model. Read with
`electron/hardening.cjs`, `electron/preload.cjs`, and `apps/desktop/SECURITY.md`.

## 1. Boundaries touched (and not crossed)

- Renderer keeps the typed `invoke`-only preload surface; Master 63 adds no
  IPC channel, no `webview` change, no `shell.openExternal` expansion, no
  filesystem/secret access. MCP add/toggle/remove go through the existing
  `aetheros:api → /api/config` path with per-call failure rollback.
- `global-status.tsx` calls `gateway.request` (the same JsonRpc client every
  view uses) — no new transport, no credential handling.
- Home's Stop action calls `session.interrupt` for the visible session id
  only; STOP ALL enumerates `session.active_list` and interrupts each —
  scoped, reported per leg, never silent.

## 2. What was NOT weakened

Context isolation, sandbox, preload boundary, IPC validation, navigation
restrictions, CSP, permission handling, secure storage — no change.
Canonical `--aether-*` aliases are pure CSS variable indirection
(no behavior). The navigation registry is a static table over existing
routes (no new protocol handlers; `aetheros://` deep links remain
unwired-by-design until a handler ships).

## 3. Verification this phase

- `npx tsc -p . --noEmit`: no errors in any touched file (pre-existing
  errors elsewhere on main untouched).
- `npx eslint` on all touched files: 0 errors.
- `npm run security:audit`: score 50/100 (12/24 passed) — pre-existing
  posture baseline, unchanged by this work (audit writes
  `apps/desktop/docs/SECURITY_AUDIT.md`; rerun after integration for
  deltas).
- Targeted `vitest` suites pass (canonical nav, emergency-stop,
  prompts/session stores). Full UI suite, visual regression, E2E, and
  performance runs were NOT executed — see certification.

## 4. Residual risks (honest)

- MCP config writes are optimistic-with-rollback; concurrent edits from
  CLI/TUI could interleave (last-writer-wins on `mcp_servers`). Mitigate
  with config revision checks when the backend offers them.
- Home exposes per-session Stop to anyone at the desktop — correct for a
  single-user OS shell; multi-user deployments need role gating (audit
  privacy §137 of the brief is not yet enforced in views).
