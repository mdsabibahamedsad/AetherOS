---
name: memory-maintenance
description: Schedule memory decay, dedup, and secret redaction.
version: 1.0.0
author: Aetheros
license: MIT
platforms: [linux, macos, windows]
metadata:
  aetheros:
    tags: [memory, cron, maintenance, decay, dedup, redaction]
    category: productivity
    requires_toolsets: [terminal]
    related_skills: []
---

# Memory Maintenance Skill

Keeps the built-in memory store healthy by running `aetherres memory maintain` on a schedule. It repairs corrupt memory files, redacts leaked secrets, merges duplicate entries, and archives stale or expired facts — then reports only when the pass actually changed something, so a recurring no-agent cron job stays silent on clean runs.

## When to Use

- User asks to "clean up my memory" or "keep my memory tidy"
- User wants scheduled memory hygiene — a recurring maintenance job
- Memory entries are accumulating duplicates, secrets, or contradictions
- User asks why memory is stale / wants decay or TTL enforcement applied

## Prerequisites

- `aetherres memory maintain` must be available (built-in CLI command — no install needed)
- The helper script `scripts/memory_maintain.py` from this skill directory
- A delivery target for cron output, if the user wants notifications
  (see `aetherres cron create --help` / `--deliver`)

## How to Run

One-off maintenance (report to the user):

```bash
aetherres memory maintain
```

Preview without mutating:

```bash
aetherres memory maintain --dry-run
```

Schedule a recurring pass. First copy the wrapper script into the cron scripts dir:

```bash
cp $AETHEROS_HOME/skills/productivity/memory-maintenance/scripts/memory_maintain.py \
   $AETHEROS_HOME/scripts/memory_maintain.py
```

Then create the job (weekly is a sane default):

```bash
aetherres cron create "every 1w" \
  --no-agent \
  --script memory_maintain.py \
  --deliver telegram \
  --name memory-maintenance
```

The `--no-agent` flag makes this a script-only job: the wrapper runs the full
lifecycle pass and emits stdout **only** when the pass changed something.
Empty stdout = silent tick, so a healthy week produces zero noise.

## Quick Reference

| Task | Command |
|---|---|
| Run a pass now | `aetherres memory maintain` |
| Dry-run preview | `aetherres memory maintain --dry-run` |
| Skip decay | `aetherres memory maintain --no-decay` |
| Skip secret redaction | `aetherres memory maintain --no-purge` |
| Skip file repair | `aetherres memory maintain --no-repair` |
| Tune decay half-life | `aetherres memory maintain --halflife-days 120` |
| Schedule weekly (no-agent) | `aetherres cron create "every 1w" --no-agent --script memory_maintain.py --deliver <target>` |

## Procedure

1. **One-off request.** Run `aetherres memory maintain` via the `terminal` tool and summarize the report. Use `--dry-run` first if the user wants to preview before any mutation.
2. **Scheduling request.** Set up the wrapper script and a no-agent cron job:
   - Copy `scripts/memory_maintain.py` into `$AETHEROS_HOME/scripts/` so the cron scheduler can find it.
   - Create the job with `aetherres cron create "every 1w" --no-agent --script memory_maintain.py --deliver <target> --name memory-maintenance`.
   - Ask the user for a delivery target if none is given (`telegram`, `discord`, `local`, `platform:chat_id`, …).
3. **Explain the cadence.** Weekly is a good default; suggest daily only for heavy use, monthly for low-use stores. The `--no-agent` script prints only when a pass changed something — clean ticks are silent.
4. **Report results.** Confirm the job ID and schedule from `aetherres cron list`. For one-off runs, tell the user what the pass did (entries decayed, secrets redacted, duplicates merged, files repaired).

## Pitfalls

1. **Forgetting the copy step.** The cron scheduler only executes scripts under `$AETHEROS_HOME/scripts/`. Scheduling the skill's script by its absolute path elsewhere will be rejected.
2. **Using the raw CLI for a scheduled job.** `aetherres memory maintain` always prints a report, so a cron job that shells out to it verbatim would message the channel every tick. The wrapper script suppresses output on no-change — use it for the scheduled path.
3. **`--no-decay` with `--no-purge` hides most of the value.** Decay is what removes stale facts; secret redaction is what stops leaks. Only skip them when the user explicitly asks.
4. **"entries decayed" appears on ongoing runs, by design.** Confidence re-normalizes on every pass until it hits its floor, so a recurring job will keep reporting decay even when there's nothing *structurally* wrong. That's genuine work, not a bug — but if the user only wants structural alerts (dedup / redaction / repair / expiry), schedule with `--no-decay` and note the trade-off: stale facts will no longer fade on their own.
4. **Delivery target mismatch.** If no `--deliver` is given the job saves output to `$AETHEROS_HOME/cron/output/` instead of messaging anywhere — confirm intent.

## Verification

- `aetherres memory maintain --dry-run` exits 0 and prints a before/after report.
- `aetherres cron list` shows the `memory-maintenance` job with mode `no-agent`.
- Run the job once with `aetherres cron run <job_id>` and confirm a report lands (or stays silent on a clean store).
- If you want to see the pass working end-to-end, add a low-confidence duplicate entry, run `aetherres memory maintain`, and confirm the duplicate is merged/archived.
