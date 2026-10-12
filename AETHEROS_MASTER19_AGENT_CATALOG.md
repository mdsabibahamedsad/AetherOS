# AETHEROS MASTER 19 — Agent Catalog

Date: 2026-08-24 · Source of truth: `agent/orchestration/catalog.py`
(`SPECIALISTS`). Risk is DERIVED from granted capabilities (P6), shown here
for planning convenience only.

| agent_id | Name | Role | Capabilities | Risk | Notes |
|---|---|---|---|---|---|
| swarm.planner | PlannerAgent | planner | MEMORY_READ | READ_ONLY | Decomposes objectives into validated task graphs |
| swarm.research | ResearchAgent | research | WEB_SEARCH, RESEARCH, MEMORY_READ | LOW | Evidence via Master 17 engine; never receives WRITE/SHELL/COMPUTER |
| swarm.browser | BrowserAgent | browser | BROWSER_READ, BROWSER_INTERACT, RESEARCH | MEDIUM | Pages remain untrusted content |
| swarm.computer_use | ComputerUseAgent | coordinator | COMPUTER_CONTROL, FILE_READ | CRITICAL | UI actions only through Master 15 control+confirmation layers |
| swarm.coding | CodingAgent | coding | CODE_EDIT, FILE_READ/WRITE, SHELL_EXECUTE, TEST_EXECUTE | HIGH | Relevant files only; runs tests; budget caps files changed |
| swarm.testing | TestingAgent | qa | TEST_EXECUTE, FILE_READ, SHELL_EXECUTE | HIGH | Triages pre-existing vs new failures |
| swarm.documentation | DocumentationAgent | writer | FILE_READ/WRITE, MEMORY_READ | HIGH | Updates only relevant docs |
| swarm.data | DataAgent | data | FILE_READ, CODE_EDIT, NETWORK_ACCESS | MEDIUM | Structured extraction/transform |
| swarm.analysis | AnalysisAgent | analysis | FILE_READ, MEMORY_READ | READ_ONLY | Findings over artifacts/results |
| swarm.verifier | VerificationAgent | verification | FILE_READ, TEST_EXECUTE, MEMORY_READ | HIGH | Independent verifier (P26); wired as `swarm.verifier` executor key |
| swarm.critic | CriticAgent | critic | — | READ_ONLY | Adversarial review; deterministic `critique()` heuristics + LLM path via adapters |
| swarm.security | SecurityAgent | security | FILE_READ, MEMORY_READ | READ_ONLY | Inspects boundaries/exfiltration; cannot weaken controls by construction |
| swarm.monitoring | MonitoringAgent | monitoring | — | READ_ONLY | Latency/errors/resources/progress/health observation |
| swarm.recovery | RecoveryAgent | recovery | MEMORY_READ | READ_ONLY | retry/rollback/re-scope/replan decisions |
| swarm.synthesis | SynthesisAgent | synthesis | MEMORY_READ | READ_ONLY | Combines VERIFIED outputs preserving conflicts/citations (P88) |

## Capability → risk floor (P6)

READ_ONLY: none · LOW: WEB_SEARCH, BROWSER_READ, MEMORY_READ, FILE_READ,
RESEARCH · MEDIUM: BROWSER_INTERACT, MCP_USE, NETWORK_ACCESS, CODE_EDIT,
TEST_EXECUTE, MEMORY_WRITE · HIGH: FILE_WRITE, SHELL_EXECUTE ·
CRITICAL: COMPUTER_CONTROL. Agent risk = max floor over granted set.

## Team formation (P63-65)

`select_team(required_capabilities)` performs greedy capability-cover over
healthy manifests (never name-based); max team size configurable.

## Runtime authority

At assignment the orchestrator computes
`GrantedCapabilities.grant(requested ∩ manifest)`; any use outside the grant
raises `CapabilityViolation` at runtime. Reputation stats (`ReputationStore`)
are ROUTING signals and are never consulted by guards or policy.
