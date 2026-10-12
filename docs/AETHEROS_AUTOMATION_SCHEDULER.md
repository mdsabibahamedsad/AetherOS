# AetherOS Automation — Scheduler (Master 43)

## Tick model

Caller-driven `tick()` (no hidden threads): due schedules → `_fire` →
run_fn → persist. VirtualClock makes every path deterministic in tests.
Production wiring calls `tick()` + `poll_watchers()` on a cadence from the
host (gateway/cron tick), plus `emit()` for event delivery.

## Time

- Canonical schedules: cron (croniter; minimal daily fallback), interval,
  once. Timezone preserved per automation (`zoneinfo`); DST via
  zone-aware arithmetic (no duplicate/skip logic needed beyond croniter).
- NL parser covers: every N minutes/hours/days/weeks, weekday at H,
  every <day> [at H], every first day of month, every day at H, in N
  units. Anything else raises ValueError (ambiguous → user rephrases).
  Preview string always returned before save.

## Durability

- Store: single atomic JSON (`autonomy.json`) + batched() coalescing
  (one write per tick burst; measured 1000-run tick in 0.63s).
- reconcile() on start: SKIP / RUN_ON_START / RUN_LATEST_ONLY /
  CATCH_UP (single run) / ASK_USER (flag, never silent backlog exec).

## Concurrency & idempotency

- concurrency_key + policy queue|skip|merge|cancel; in-tick lock map.
- Idempotency key `automation:kind:minute-window`; duplicates counted,
  not executed. RunRecord carries execution_id + key end to end.

## Retry

Exponential backoff (base×2^attempt, cap, optional jitter), retryable vs
non-retryable lists, max attempts; destructive workflows excluded from
auto-retry entirely.

## Recursion & rate limits

Causal chain (max depth 5) + cycle detection + 10 fires/min/automation.
Automation→trigger→automation loops terminate with metrics proof.
