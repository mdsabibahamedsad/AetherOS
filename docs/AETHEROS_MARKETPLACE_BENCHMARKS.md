# Marketplace Benchmarks

Status: measured locally (Windows, Python 3.12, pytest). Command:

```
.venv/Scripts/python.exe -m pytest tests/agent_market/test_benchmarks_market.py -s
```

## Results (best-of-N, this machine)

| Benchmark | Result |
|---|---|
| discovery @1 / 10 / 100 / 1000 agents | 0.14 / 0.26 / 1.50 / 17.54 ms |
| rank 1000 candidates | 4.90 ms |
| full pipeline (delegate+complete, free) | 67.33 ms |
| search over 10,000 in-memory listings | 69.83 ms |

## Scaling notes

- Batched single-pass trust/reputation aggregation fixed an O(n²)
  blowup (1000-agent discovery: 11,620ms → 17.5ms, ~660x).
- 10k search is in-memory; persistent bulk import at that scale is
  BLOCKED (per-write full-file JSON rewrites are O(n²)) — pagination +
  incremental loading are implemented in the UI; renderer virtualization
  is PLANNED.
- No remote latencies are reported anywhere: no live peers exist, and
  inventing them is forbidden. LAN/remote figures: NOT EXECUTED.

## Economic benchmarks

Cost per successful/verified task, refund rate, failed-task cost,
fallback cost, verification cost, quote variance: derivable from the
ledger per deployment; no production traffic exists here, so values are
NOT EXECUTED (not zero — unknown). The accounting denominators
(estimates vs settled actuals) are implemented and tested.

## Reputation benchmarks

Honest/unreliable/new/Sybil/colluding/review-spam agents are covered
as deterministic adversarial tests (ranking remains robust by
verified-weighting + flags), not as statistical benchmark runs.
