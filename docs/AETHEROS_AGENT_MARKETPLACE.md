# AetherOS Agent Marketplace

Status labels used across marketplace docs: **IMPLEMENTED**,
**PARTIALLY_IMPLEMENTED**, **PLANNED**, **BLOCKED**.

## What it is (IMPLEMENTED)

A policy-driven delegation layer over the Agent Network. AetherOS can
discover external agent services, evaluate them deterministically,
negotiate contracts, enforce budgets, authorize payment, verify results,
settle, and update reputation — every step observable and auditable.

Backend: `aetheros_agent_market/` (Python). UI: Marketplace Center
(`/agent-marketplace`). CLI: `aetheros agent-marketplace ...` (`marketplace`
alone is the pre-existing Extension Marketplace). IPC:
`marketplace.*`.

## Economy model (IMPLEMENTED)

Money is integer minor units + ISO currency. Providers: `none` (free,
still ledger-audited), `credits` (local test pool, NOT real money),
`org_budget` (budget envelope, no real rail). External rails integrate
via `PaymentProvider` — none is configured; `external:*` is refused
with an explicit error until integrated (no fake payments).

Lifecycle per delegation: quote → contract → budget reserve → approval
(if tier requires) → authorize → execute → verify → capture, else
void/refund/dispute. Escrow is an abstraction only (PLANNED — no
provider implements conditional settlement yet).

## Trust & reputation (IMPLEMENTED)

Trust is 7-dimensional with decayed, provenanced signals. Reputation is
13 metrics with value/confidence/sampleCount/timeWindow/provenance.
Single-number scores are never shown; empty metrics read
"insufficient evidence". Attack defenses: verified-transaction
weighting, min samples, burst/single-org/reciprocal flags. Flags never
auto-blacklist.

## Safety defaults (IMPLEMENTED)

`remote_delegation`, `paid_agents`, `automatic_negotiation`,
`automatic_payment`, `external_registries`, `organization_marketplace`
all default OFF. STOP ALL + kill switches are operator-audited.
Simulation fixtures are SIMULATION-marked and storage-isolated.

## Not claimed (BLOCKED)

Live remote delegation (no external peers in test env), external A2A
interop runs, real-money rails, AV-engine artifact scanning, formal
injection guarantees, cross-platform marketplace validation, bulk
import at 10k scale (per-write JSON stores are O(n²) — measured, see
benchmarks doc).
