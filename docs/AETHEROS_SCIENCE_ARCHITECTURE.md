# AETHEROS_SCIENCE_ARCHITECTURE — Component Architecture

```
ScientificIntelligenceEngine (facade, autonomy L0–L5, budgets, audit)
├── Research: decompose_question, ResearchLandscapeBuilder,
│   KnowledgeGapDetector, SourceIndependenceAnalyzer, ContradictionEngine
├── Hypotheses: HypothesisEngine (13 strategies), HypothesisDiversifier,
│   NoveltyAnalyzer, HypothesisCritic, FalsificationEngine,
│   ExplorationController
├── Experiments: ExperimentDesigner (+branching/DAG-ready parent links),
│   ComputationalRuntime (subprocess sandbox, manifests, checkpoints,
│   idempotency fingerprints), ExperimentSimulator (Master-52 bridge),
│   ActiveExperimentSelector (value/cost)
├── Statistics: descriptives, CI, Welch-t, Cohen's d, Pearson, bootstrap,
│   permutation, OLS, power/sample-size, Holm/Bonferroni/FDR
├── Evidence: EvidenceEngine (E0–E6, weighting), BayesianUpdater
│   (Beta-Binomial), ReproducibilityEngine, NegativeResultMemory
├── Knowledge: ScientificKnowledgeGraph (provenance-required edges,
│   §115 queries), ScientificMemory (chronology, lessons)
├── Discovery: DiscoverySynthesizer (no-skip state machine),
│   QualityGate (10 checks), ReplicationEngine, RedTeamScientist,
│   debate(), ReportGenerator, causal/discovery language guards,
│   verify_numeric_claims
├── Safety: ScientificSafetyPolicy, LabConnector (LAB_UNAVAILABLE default)
└── Benchmarks: ScientificBenchmarkEngine + golden/adversarial fixtures
```

## Integration (extends, never duplicates — §220)

- Master 50: `_gate()` per privileged op; provisioned `science-engine`
  service identity (trust never self-granted); emergency stop wired to
  `stop_all()`; audit events on task/stop/discovery.
- Master 51: prediction errors/lessons feed improvement loop;
  evaluation infra reusable for benchmark categories.
- Master 52: `ExperimentSimulator(cognitive)` bridge; anomaly records
  map to PredictionError; counterfactual planning for discriminating
  experiments; digital-twin modes reused.
- Research/Memory/Swarm/Automation/A2A/MCP/Model Hub: seam points
  documented; network research requires injected `search_fn`
  (default LOCAL_ONLY, landscape honestly source-less without it).

## Storage

File-backed stores under the engine home (`runs/`, fingerprints,
checkpoints). Normalized DB tables (§87) deferred — schema modeled in
`models.py`; migration to persistent DB is a tracked blocker, not
claimed done.
