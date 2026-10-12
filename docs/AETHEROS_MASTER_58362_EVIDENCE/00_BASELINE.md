# AETHEROS MASTER 58362 — Baseline Reproduction (2026-10-12)

## Paths verified
- Root: `D:\hermes-agent-main` (exists, not a git checkout — same as 58361)
- Project: `D:\hermes-agent-main\aetheros`
- Desktop source: `aetheros/apps/desktop/src`
- Prior report: `aetheros/docs/AETHEROS_MASTER_58361_UI_REDESIGN_REPORT.md` (read)
- Prior evidence: `aetheros/docs/AETHEROS_MASTER_58361_EVIDENCE/` (00–05 read)

## 58361 fixes confirmed still in place (grep, before new edits)
- `left-sidebar.tsx`: `navIdForPathname` + `routedSection` present (6 matches)
- `topbar.tsx`: `$activeProfile` pill present (5 matches)
- `home/index.tsx`: `stashAndGo` present (3 matches)
- `app-shell.tsx`: no `components/command-palette` mount; single palette mount in
  `desktop-controller.tsx:966` (+ Jarvis's own scoped palette, by design)
- `shell/context-panel.tsx`: absent (deleted in 58361, no dangling imports)

## Baseline test reproduction (before new edits)
- `npm run typecheck` (`tsc -p . --noEmit`): CLEAN, exit 0
- `npx vitest run`: **134 files / 891 tests PASS**, 0 fail (44.83s) — matches 58361

## Dev-server smoke (new, this pass)
- `vite --host 127.0.0.1 --port 5175` serves the renderer: `HTTP 200` on `/`
  with the expected `index.html` bootstrap. Server stopped afterwards.
- This proves the dev workflow serves; it is NOT packaged-app validation.

## Prior status adopted
`AETHEROS_UI_REDESIGN_PARTIAL` (58361). Previously closed fixes stay closed;
only fresh-evidence regressions may reopen them (none found).
