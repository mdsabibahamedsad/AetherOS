# AETHEROS MASTER 58363 — Workflow Acceptance Matrix (2026-10-12)

Legend: PASS (executed live) · CODE-OK (traced in source + unit-tested, no live
run) · BLOCKED (needs live gateway/model/mic/packaged app — unavailable here).
No live gateway, provider key, microphone session, or fresh package exists in
this environment; nothing below fabricates them.

| Workflow | Check | Verdict | Evidence |
|----------|-------|---------|----------|
| A1 | Home/Chat submit reaches canonical runtime | CODE-OK | stash→take→`prompt.submit` chain read; `submitPromptText` guard tested by existing suite |
| A2 | Model/tool selection | BLOCKED | server-side routing; needs live gateway |
| A3 | Real execution events/progress | CODE-OK | `tool.start/complete`, `message.complete`, stall/timeout handling read; streaming tests exist |
| A4 | Result ↔ conversation association | CODE-OK | session-id plumbing read; session tests exist |
| A5 | Honest errors | CODE-OK | UNAVAILABLE/FAILED/TIMEOUT states + Models error shell (58362) |
| B | Tool input validation/invocation/result/timeout | BLOCKED (live) | needs gateway agent; failure paths CODE-OK (tool cards show error/warning, timers, copy) |
| C1 | Jarvis enter/exit, session preserved | CODE-OK | exit → `/home`, no teardown (read); voice-exit local intent tested |
| C2 | Jarvis text command | CODE-OK | `submitJarvisCommand` gateway/local paths unit-tested incl. new busy tests |
| C3 | Voice permission/capture/transcription | CODE-OK | real `getUserMedia`/meter/STT gating read; mic-live ⇔ LISTENING only |
| C4 | Voice unsupported → clear explanation | CODE-OK | `checkAvailable` gates + ERROR + spoken/visible message (read) |
| C5 | Cancel/retry/recovery | CODE-OK | Esc → pipeline cancel + voice cancel; CANCELLED ≠ FAILED; reload/edit resend (read) |
| C6 | Background tasks discoverable after exit | CODE-OK | no teardown on exit; Activity drawer + Tasks views read live stores |
| C7 | Approvals reviewable/resolvable | CODE-OK | Security Center approvals wired to `approval.respond` (58362 screen audit) |
| D1 | Lifecycle queued→running→…→completed/failed/cancelled | CODE-OK | `task-state-machine` + `jarvis-lifecycle` tests; chat `interrupted` flag |
| D2 | Stable IDs, task↔session link | CODE-OK | `cmd-`/`agent-` ids; command log carries `sessionId` |
| D3 | Duplicate-submit prevention | **FIXED+TESTED** | H-1: guards at `submitJarvisCommand` (all entries), `runCommand`, both composers; 4 new tests |
| D4 | Timeout/cancel behavior | CODE-OK | 180s pipeline TIMEOUT; `session.interrupt`; Jarvis cancel flag |
| D5 | Persistence across restart | NOT SUPPORTED | command log is in-memory (no claim made) |
| E1 | Draft retention across routes | CODE-OK | null-scope stash↔take contract tested (`composer.test.ts`); per-thread swap read |
| E2 | Sidebar after refresh/deep-link/history | TESTED | `left-sidebar.test.ts` mapping (58362) |
| E3 | Single palette, intended entries only | CODE-OK | one mount + focus restore; shortcuts `mod+k/mod+p` (read) |
| E4 | Panels optional on Home | VERIFIED | dead rail deleted (58361); file-browser chat-scoped/closed |
| E5 | Task identifiability across entries | CODE-OK | Tasks view merges cron+action sources with stable ids (58362 fix) |
| F1 | Provider/gateway down | CODE-OK | UNAVAILABLE + actionable message; Models retry shell |
| F2 | Tool error/timeout/bad args | CODE-OK | tool-card error states; pipeline TIMEOUT (read) |
| F3 | User cancel / approval reject | CODE-OK | CANCELLED distinct; reject prevents run (tested pattern) |
| F4 | Navigation during active task | CODE-OK | state preserved; draft swap; no teardown (read) |

## Approval/permission audit (§5, renderer scope)
- Jarvis local actions: `decideCapability` policy gate; `ask` → `ApprovalRequiredError`
  before anything runs (unit-tested both channels). No alternate UI entry bypasses
  `submitJarvisCommand` (command-bar, command-input, palette sink, voice all funnel).
- Gateway destructive phrasing: same gate pre-pipeline; Allow-once resubmits the
  exact command. Backend approval parks the agent until resolved (read).
- Agent-Manager Remove is list-only (session untouched, titled honestly).
- No credential or shell access added to the renderer; preload/IPC untouched.

## Observability (§6)
Chain present without a second logging system: request → `cmd-` id →
`$jarvisCommandLog` (timestamp, sessionId, inputType, intent, status,
durationMs, toolsUsed, result ≤2000 chars, error) → notifications. No secrets
in records (names/statuses only).
