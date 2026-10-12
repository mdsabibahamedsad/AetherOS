# AetherOS Cognitive Architecture 2.0 (Master 52)

Package `aetheros_cognitive/` implements the canonical loop
PERCEIVE → STATE ESTIMATE → WORLD UPDATE → CAUSAL ANALYSIS →
CANDIDATES → FORESIGHT → SIMULATE → SCORE → POLICY CHECK → EXECUTE →
OBSERVE → PREDICTION ERROR → MODEL UPDATE (§2).

Modules: `models` (WorldState, Entity, ActionCandidate, FutureBranch,
PredictionConfidence, PredictionError, CausalEdge, SimulationBudget —
all predictions tagged PREDICTION, §0.4) · `world_state`
(StateEstimator: authority/freshness conflict resolution, snapshots,
staleness, task projections §166) · `world_models` (Rule-Based,
State-Transition, Graph-Dynamics, LLM-seam reporting UNAVAILABLE,
Hybrid with §49 disable, ensembles + disagreement) · `simulator`
(budget rollouts, Monte Carlo frequencies labeled simulation-only,
SideEffectFirewall §122) · `planner` (beam, best-first, A*, MCTS-lite —
real implementations; documented SCORE_WEIGHTS; policy pruning;
reversibility tie-breaks) · `foresight` (VoI-gated SIMULATE/SHALLOW/
DEEP/ASK_USER, horizon penalty, Brier calibration) · `reality`
(expect-before-act, expected-vs-actual, divergence replan/stop,
TOCTOU recheck) · `counterfactual` (generate/simulate/compare/rank/
explain) · `causal` (HYPOTHESIS until rule/domain/experiment/
intervention validation; observation never validates §19) ·
`twins` (Repository/Browser/Automation/Swarm/A2A/MCP — overlay copies,
dry-runs, mocks labeled mock≠real) · `router` (6 modes, user
Fast/Balanced/Deep/Max, degradation chain) · `cognition` (facade:
M50 policy gate precedes execution, M51 error feed, red-team,
approval packets, CognitiveAuditEvents).

Backends actually used: RULE_BASED + STATE_TRANSITION +
GRAPH_DYNAMICS (+HYBRID orchestration). LLM/NEURAL/EXTERNAL: honest
UNAVAILABLE stubs — no fabricated futures (§0.1–0.3).
Security: prediction never overrides policy/approval/DLP (§0.8);
simulated tools firewall-contained (§121–124); poisoning guarded by
source/provenance/confidence (§118–119). Limitations: no AGI claims
(§181); research/browser/computer/terminal/DB/API twins are state
sketches, not live integrations; Cognitive Center desktop UI not
built (CLI covers ops); twins validated against scripted scenarios,
not production workloads.
