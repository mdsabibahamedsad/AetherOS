---
sidebar_position: 18
title: "Memory Maintenance"
description: "Keep the built-in memory store healthy — repair corrupt files, redact leaked secrets, merge duplicates, and decay stale entries — on a schedule or on demand."
---

# Memory Maintenance

The built-in memory store gets written by the agent every session. Over time that means duplicate facts, contradictory entries, stale or expired facts, and the occasional leaked secret. `aetherres memory maintain` runs a single lifecycle pass that repairs the store, redacts secrets, resolves contradictions, merges duplicates, and decays or archives old entries — and this guide shows how to run it on demand or wire it into a scheduled, silent-until-it-changes cron job.

## What the pass does

One `maintain` pass runs five stages, in order:

| Stage | What it fixes |
|---|---|
| **Repair** | Corrupt/drifted memory files are backed up and rewritten as a clean §-delimited entry list; the search index is rebuilt. |
| **Secret redaction** | API keys, tokens, and passwords found in memory entries are replaced with a placeholder and flagged. |
| **Conflict resolution** | Contradictory attribute/polarity entries are resolved (keep-best), so a later merge can't swallow a fact. |
| **Reconsolidation** | Near-duplicate entries (token similarity ≥ 0.8) are merged keeping the highest-confidence one; over-budget stores archive lowest-priority entries. |
| **Decay** | Confidence decays by `0.5 ** (age / halflife)` toward a 0.05 floor; TTL-expired entries are archived. |

The whole thing is idempotent: a clean store produces a clean pass with zero mutations.

## Run it on demand

```bash
aetherres memory maintain
```

Flags:

```bash
aetherres memory maintain --dry-run        # preview, no mutation
aetherres memory maintain --no-decay       # skip the decay pass
aetherres memory maintain --no-purge       # skip secret redaction
aetherres memory maintain --no-repair      # skip file repair
aetherres memory maintain --halflife-days 120   # slower decay
```

Output shows the store state before and after, plus per-stage counts:

```
  Memory state before: 42 entries (31 memory / 11 user), 1 potential secrets
  Done:
    • repair: 0 rewritten, 0 backed up
    • secrets: 1 found, 1 redacted
    • duplicates: 2 merged, 0 archived over budget
    • decay: 3 decayed, 0 expired

  Memory state after:  36 entries (26 memory / 10 user), 0 potential secrets
```

## Schedule it (silent until it changes)

For recurring hygiene, copy the skill's wrapper script into the cron scripts dir and schedule it as a **no-agent** job:

```bash
aetheros skills install official/productivity/memory-maintenance

cp $AETHEROS_HOME/skills/productivity/memory-maintenance/scripts/memory_maintain.py \
   $AETHEROS_HOME/scripts/memory_maintain.py

aetherres cron create "every 1w" \
  --no-agent \
  --script memory_maintain.py \
  --deliver telegram \
  --name memory-maintenance
```

The wrapper runs the full `maintain` pass and prints a report **only** when the pass actually changed something. Empty stdout is a silent tick, so a healthy week produces zero messages; the day the store needs work, the report lands in your chat.

> **Note on "entries decayed":** confidence decay re-normalizes on every pass until an entry hits its floor, so a recurring job may report `entries decayed: N` even when nothing else is wrong — that's genuine, expected work. If you only want *structural* alerts (dedup / redaction / repair / expiry), schedule with `--no-decay` and accept that stale facts no longer fade on their own.

Verify it fires:

```bash
aetherres cron list
aetherres cron run memory-maintenance
```

See [Script-Only Cron Jobs](/guides/cron-script-only) for the full no-agent semantics (delivery targets, editing, lifecycle).

## Why not run the CLI itself as the cron script?

`aetherres memory maintain` always prints a report, even on a clean pass. A cron job that shells out to it verbatim would message your channel every tick, week after week. The wrapper script's empty-stdout-on-no-change behavior is what makes scheduled maintenance practical.

## Configuration

There is no dedicated `memory` maintenance config section — the lifecycle pass uses the store's existing entry metadata (`confidence`, `ttl`, `archived`, `pinned`). `halflife_days` defaults to 90 and is only tunable per-run via `--halflife-days` (or the wrapper's same flag). Pinned entries are exempt from decay, dedup archiving, and TTL expiry.

## Related

- [Automate Anything with Cron](/guides/automate-with-cron) — LLM-driven cron patterns.
- [Script-Only Cron Jobs](/guides/cron-script-only) — the no-agent watchdog pattern this uses.
- [Scheduled Tasks (Cron) reference](/user-guide/features/cron) — full schedule syntax and lifecycle.
