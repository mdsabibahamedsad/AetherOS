# AETHEROS_SCIENTIFIC_BENCHMARKS — Design + Measured Results

## Design

Categories RQ/HG/HD/HN/HF/ED/CS/SA/PR/FA/RP/DA/CI map to objective
graders (deterministic checks, golden fixtures, adversarial
fixtures). No LLM judge anywhere. Baselines compare repeated trials
with mean/variance reported; improvement percentages only from
measured deltas.

## Measured results (2026-09-07, Windows 11, Python 3.11)

`python benchmark/science_bench.py` → 21/21 trials passed:

- SA mean-shift golden: SUPPORTS (3/3)
- SA null golden: INCONCLUSIVE, never SUPPORTS (3/3)
- CS perfect-correlation golden: r=1.0 (3/3)
- HG generation ≥10 strategies (3/3), HF criteria present (3/3)
- CI fake-citation unresolvable (3/3), PR injection quarantined (3/3)

## E2E demo (§235, real execution)

"Which sort is faster on n=400 random ints": insertion 1.89 ms vs
timsort 0.02 ms (~76×), outcome INCONCLUSIVE at n=1/group (honest —
single-sample comparison is not confirmatory), replication
REPRODUCED within tolerance, next experiment proposed (vary n +
input order). Conclusion explicitly scoped to one context.

## Performance smoke

100 task creations < 10 s (measured ~instant); 6 concurrent
experiments, no corruption; per-category latency < 0.1 ms for
in-memory ops; experiment wall-time dominated by subprocess runs.
