# Agent Network Benchmarks (Master 46 §§137–141)

Method: `tests/agent_network/test_benchmarks.py` — real local code
paths, 50–200 samples each, P50/P95 reported. Run:

```bash
.venv/Scripts/python.exe -m pytest tests/agent_network/test_benchmarks.py -q -p no:cacheprovider -s
```

## Local operation latency (measured 2026-09-05, Windows, Python 3.12)

| Operation | P50 | P95 | Cap asserted |
|---|---|---|---|
| Agent Card parse + validate | <1 ms | <50 ms | P95 < 50 ms |
| Authz decision + DLP scan | <1 ms | <50 ms | P95 < 50 ms |
| Route across 100 candidates | <5 ms | <100 ms | P95 < 100 ms |
| Trust-store read | <1 ms | <50 ms | P95 < 50 ms |

(Exact figures print in test stdout; the caps above are the asserted
regression gates. Re-run on your hardware for absolute numbers.)

## Delegation/routing comparisons

Single-agent vs local swarm vs remote vs hybrid quality/latency/cost:
**not measured** — no live remote peers exist in CI, and inventing
numbers would violate the evidence rule. The router's trust-first
ordering and SLA filters are covered deterministically in
`test_router.py`; relationship reliability accumulates only from real
delegations (`record_relationship`).

## Network metrics

LAN vs remote latency/throughput/failure/cost: **UNKNOWN** (no peers).
Recorded as `UNKNOWN` in `test_benchmarks.py` by rule, not by omission.

## Security benchmark

Attack fixtures in `test_adversarial.py` (spoof, injection, SSRF,
exfiltration, duplication, flood, escape, rate-limit): all contained
paths assert denial/containment; allow-paths assert explicit approval.
No false-negative/positive rates are claimed — the suite is a
containment gate, not a statistical benchmark.
