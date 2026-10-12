# AetherOS Provenance

Implementation: `kernel/core/provenance_engine.py` (nodes/edges/lineage),
`kernel/core/audit_engine.py` (hash-chained log), `kernel/core/observability_engine.py`
(traces/metrics).

Provenance types (§24): `user_provided`, `model_generated`,
`tool_returned`, `web_derived`, `memory_derived`, `sensor_derived`,
`device_derived`, `agent_derived`, `human_approved`, `system_derived`,
`inferred`, `simulated`, `predicted`, `verified`, `unverified`.

Rules: inference is never presented as fact, simulation never as reality,
prediction never as observation. Mocks/fixtures carry explicit
`REAL / SIMULATED / MOCKED / RECORDED / REPLAYED` labels (§57); hardware
claims use `SIMULATION / REPLAY / MOCK / HARDWARE_UNAVAILABLE /
LIVE_HARDWARE` (§116).

Tracing (§53): `trace_id / span_id` across user → intent → agent → model /
tool / child / memory / external effect; the Kernel debugger surfaces live
agents, authority, resources, context, approvals, policy decisions, traces,
checkpoints, failures, and recovery attempts.
