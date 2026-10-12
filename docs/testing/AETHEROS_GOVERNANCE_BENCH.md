# GovernanceBench (§101) — how to run, what was measured

```bash
PYTHONPATH=. python benchmark/governance_bench.py
```

Results on Windows 11, Python 3.11 (2026-09-07, this machine):

| operation | n | p50 | p95 | p99 |
|---|---|---|---|---|
| authorization_check (full pipeline) | 1000 | ~40µs | ~50µs | ~66µs |
| policy_evaluate | 1000 | 2.5µs | 2.6µs | 3.5µs |
| trust_assess | 1000 | 11.5µs | 19.5µs | 30.1µs |
| identity_lookup | 1000 | 0.4µs | 0.4µs | 0.5µs |
| delegation_grant | 200 | 5.7µs | 8.9µs | 18.2µs |
| control_plane OFF (baseline) | 1000 | 0.1µs | 0.2µs | 0.2µs |
| control_plane ON (full check) | 200 | 39.7µs | 71.6µs | 143.7µs |

Verdict: §88 target (sub-ms to low-ms local evaluation) met with large
margin. Overhead vs OFF ≈ +40µs per privileged action — negligible next
to any model call. Re-run on your hardware; never quote these numbers
as guarantees.
