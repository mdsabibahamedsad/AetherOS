# AETHEROS MASTER 58366 — Ranked Backlog & Selection (2026-10-12)

## P0 — Essential reliability
1. **H-2 Task lifecycle actions in Tasks view** — DONE THIS PHASE. Runtime had
   pause/resume/trigger/delete; UI exposed only "view". Wired + tested.
   (Small; offline-verifiable; no new deps.)
2. Desktop action-task restart persistence — DEFERRED (backend store design
   decision; needs owner/product call, not a drive-by).
3. Live model/provider fallback drill — BLOCKED_EXTERNAL (needs creds).

## P1 — Core assistant capabilities
4. Models UI fallback-health surfacing — deferred (needs live providers).
5. Live voice session — BLOCKED_EXTERNAL (mic + STT/TTS providers).
6. Memory recall quality eval — BLOCKED_EXTERNAL (gateway).
7. Real browser nav/download wiring — deferred (Electron-API work + display).
8. Command-log restart persistence — deferred (pairs with #2).
9. Live delegation trace — BLOCKED_EXTERNAL.

## P2 — Advanced ecosystem
10. Versioned skill/agent distribution trust — no demanding user evidence; parked.
11. Sync/remote E2E verification — BLOCKED_EXTERNAL.
12. Visual workflow builder — REJECTED (backend supports scheduled jobs, not graphs).

## Selection rationale (H-2)
Highest value × feasible: every scheduled-task user hits the Tasks list, which
could display but not manage work — the exact "polished but unusable" gap this
mission targets. Bounded root cause (missing UI calls, proven runtime methods,
established Cron-overlay pattern), deterministic tests, zero security change
(uses existing gateway methods; destructive delete confirmed; action rows
honestly view-only since no stop endpoint exists).
