# AETHEROS BENCHMARK REPORT

_Generated from artifacts only · 2026-08-24 09:50 UTC_

## Methodology

- Same task text for every agent (P5); same scoring validators (P44).
- Same-model rule enforced via fairness fingerprint; violations emit FAIRNESS_WARNING (P4/P19-20).
- BLOCKED executions are preserved with reasons (P9/P12).
- Claims are generated exclusively from measured artifacts; missing data yields INSUFFICIENT EVIDENCE (P62/63).

## Dataset quality control

- dataset integrity: v1, 100 tasks, hash `3cbbabb25f9efc6f` → OK
- validator registry: 12 deterministic validators
- trace capture: no traces yet (no live runs)

## Leaderboard

| Rank | Agent | Overall | Verified Success | P50 ms | Tokens/task | Cost/task | Reliability | Safety events |
|---|---|---|---|---|---|---|---|---|
| – | claude-code (all runs BLOCKED (never executed)) | – | – | – | – | – | – | – |
| – | hermes (all runs BLOCKED (never executed)) | – | – | – | – | – | – | – |

## Head-to-head: AetherOS vs Hermes

No executed head-to-head between `aetheros` and `hermes` exists yet — INSUFFICIENT EVIDENCE.

## Evidence-gated claims

### AetherOS vs hermes

- INSUFFICIENT EVIDENCE (INSUFFICIENT_EVIDENCE: need results for both 'aetheros' and 'hermes'; have ['claude-code', 'hermes'])

### AetherOS vs openclaw

- INSUFFICIENT EVIDENCE (INSUFFICIENT_EVIDENCE: need results for both 'aetheros' and 'openclaw'; have ['claude-code', 'hermes'])

### AetherOS vs openhands

- INSUFFICIENT EVIDENCE (INSUFFICIENT_EVIDENCE: need results for both 'aetheros' and 'openhands'; have ['claude-code', 'hermes'])

### AetherOS vs claude-code

- INSUFFICIENT EVIDENCE (INSUFFICIENT_EVIDENCE: need results for both 'aetheros' and 'claude-code'; have ['claude-code', 'hermes'])

### AetherOS vs codex

- INSUFFICIENT EVIDENCE (INSUFFICIENT_EVIDENCE: need results for both 'aetheros' and 'codex'; have ['claude-code', 'hermes'])

## Tradeoffs observed

- no executed pairs available for tradeoff analysis

## Limitations

- Agents without installed CLIs are NOT_TESTED, never scored.
- Live runs cost tokens and execute only behind explicit `--allow-live`.
- Cross-environment comparisons carry fairness warnings.
