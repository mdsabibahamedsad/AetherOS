# AETHEROS MASTER 20 — BENCHMARK SPEC

Scope: how benchmarks, baselines, comparisons and artifacts behave in the
Master 20 layer (`agent/quality/benchmarks.py`, `datasets.py`).

## 1. Check contract

A benchmark check is a registered callable returning `Dict[str, float]`.

```python
from agent.quality.benchmarks import BenchmarkCheck, BenchmarkEngine

engine = BenchmarkEngine()
engine.register(BenchmarkCheck(
    name="suite", category="functional",          # functional|performance|
    domains=frozenset({"memory"}),                #   security|reliability|quality
    fn=lambda: {"task_success_rate": 0.97},
    critical=True))
run = engine.run(target="agent-core", version="1.2.0",
                 baseline=baseline, policy=ComparisonPolicy())
```

- Metrics produced under a check name `N` are stored as `N.<metric>`;
  comparison-policy sets match on the dotted suffix so policy names stay
  stable across check namespaces.
- A raising check records `run.failures` and never fabricates a metric;
  critical failures additionally raise warnings.
- `run.status` must be COMPLETED before `BenchmarkEngine.publish()` accepts
  it — unexecuted/pending runs are refused (anti-fabrication, P17/P18).

## 2. Baselines (P3/P45)

`BaselineStore` persists baselines (label, version, metric snapshot) under
`get_aetheros_home()/quality/baselines.json`. "Latest" resolves by recorded
time; equal timestamps resolve deterministically to the last-recorded entry.
Every optimization claim must reference a stored baseline; no baseline ⇒ no
improvement language (P19).

## 3. Comparison & blocking (P46-47)

`ComparisonPolicy`:
- `max_regression_pct` (default 10.0) — configurable, never universal law;
- `block_on_regression` = {task_success_rate, verified_success_rate,
  availability, p95_latency_ms} — a regression beyond threshold on these
  BLOCKS release;
- `higher_is_better` set drives delta direction; latency-class metrics are
  lower-is-better by construction.

Deltas are absolute + percent with ±0.5% deadband (`unchanged`), otherwise
`improved`/`regressed`; baseline-missing metrics are `new` and never block.

## 4. Reproducibility & artifacts (P90-91)

Every `EvaluationRun` records code commit, python version, platform and a
timestamp; result payloads carry a SHA-256-derived `artifact_hash`
(content-stable, sort_keys). Store artifacts alongside the hash so any
published number can be re-derived from its bytes.

## 5. Golden datasets (P30-31)

`DatasetRegistry`: create-once naming, explicit `change_note` on every new
version, rejection of byte-identical successor versions, full history
retention, `verify_integrity(name, version)` against the content hash.

## 6. Golden evaluation suite SC01–SC30 (P95)

Implemented in `tests/quality/test_golden_scenarios.py`. Honesty policy:
real offline verification where possible; otherwise an explicit skip with
the authoritative validation venue. Current local status (Windows box,
2026-08-24):

| ID | Scenario | Local result |
|---|---|---|
| SC01 | core tool discovery (terminal/file/web) | PASS |
| SC02 | coding surface (code_execution + file tools) | PASS |
| SC03 | browser automation | SKIP → CI e2e job |
| SC04 | computer-use | SKIP → macOS-only |
| SC05 | research citation coverage | PASS |
| SC06 | memory_os structure | PASS |
| SC07 | multi-agent collaboration manager | PASS |
| SC08 | MCP stack constructibility | PASS |
| SC09 | checkpoint secret redaction | PASS |
| SC10 | prompt-injection containment (context isolation) | PASS |
| SC11 | exfil payload redaction | PASS |
| SC12 | permission nesting restores outer principal | PASS |
| SC13 | performance measurement pipeline | PASS |
| SC14 | stress availability | PASS (opt-in via --run-stress) |
| SC15 | soak | SKIP → long-horizon CI |
| SC16 | seeded chaos harness recovery | PASS |
| SC17 | recovery-score determinism | PASS |
| SC18 | checkpoint roundtrip | PASS |
| SC19 | installer | SKIP → build-windows-installer.yml etc. |
| SC20 | upgrade path | SKIP → upload_to_pypi.yml |
| SC21 | Windows paths/profile | PASS |
| SC22 | macOS | SKIP (not this host) |
| SC23 | Linux | SKIP (not this host) |
| SC24 | CLI API compatibility (command registry) | PASS |
| SC25 | config compatibility (merge + unknown keys + version) | PASS |
| SC26 | regression classification end-to-end | PASS |
| SC27 | model evaluation vs baseline (blocking) | PASS |
| SC28 | tool evaluation (success + latency) | PASS |
| SC29 | agent reputation (routing metadata) | PASS |
| SC30 | full release-certification workflow incl. rollback | PASS |

Platform claims (SC22/SC23) are only ever counted on hosts running them;
installer/upgrade claims only inside the CI jobs that actually execute
them. No scenario counts a skip as a pass.
