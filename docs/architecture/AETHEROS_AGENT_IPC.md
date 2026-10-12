# AetherOS Agent IPC

Transport: `kernel/event_bus.py` (pub/sub) + `kernel/inter_agent.py`
for the legacy multi-agent bus; the canonical envelope is
`kernel/core/types.py::KernelEvent`.

Envelope: `event_id`, `topic`, `source`, `agent_id`, `process_id`,
`task_id`, `intent_id`, `trace_id`, `span_id`, `parent_span_id`, `data`,
`provenance`, `timestamp`, `schema_version`.

Verbs (§19): `request / response / stream / event / subscription /
handoff / delegation / cancel / pause / resume / checkpoint / error /
approval`. Event families (§25): agent.*, intent.*, capability.*,
resource.*, memory.*, model.*, tool.*, approval.*, policy.*, security.*,
checkpoint.*, device.*, research.*, automation.*.

Contracts (§67): typed, schema-validated, versioned IPC — malformed
messages are rejected, never coerced. A2A (§20) and MCP (§21) both enter
through the capability/authority pipeline: remote agents carry identity,
trust, capability declarations, budgets, rate limits, contracts, and
provenance, and can never directly invoke privileged local capabilities.
MCP stays a tool/data layer *under* AetherOS authorization — never a
bypass.
