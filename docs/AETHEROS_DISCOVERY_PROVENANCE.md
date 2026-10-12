# AETHEROS_DISCOVERY_PROVENANCE — Provenance + Audit Design

## Chain

Discovery → Claims → Evidence (E0–E6, weighted, independence-tagged)
→ Experiments (manifests, fingerprints) → Raw Data (immutable,
hashed) → Code (snapshotted per run) → Environment (python/platform,
deps, seeds, hardware slot).

## One-click audit (`discover` + graph + artifacts)

1. All evidence ids resolve in the evidence store.
2. All artifacts exist on disk (missing → audit FAILS; tested).
3. Hashes match recorded values.
4. Citations resolve to provided sources (fake → fails).
5. Numbers in reports match source metrics (`verify_numeric_claims`;
   mismatch → REPORT_BLOCKED).
6. Reproduction status current.

## Versioning & immutability

Hypotheses versioned per experiment (prior_history appended, never
rewritten). Raw data files never overwritten (per-run directories).
Data exclusions logged with reason/rule/who/timestamp. Discovery
state machine forbids skipping; full `state_history` retained.

## Traceability

Every task carries a `ResearchTraceEvent` log (who/agent, what, when,
why, input, tool, model, data, decision, result, evidence,
confidence). Report sentences map to claim→evidence→source→experiment
via `ReportGenerator` structures (UI "Explain this sentence" seam).
