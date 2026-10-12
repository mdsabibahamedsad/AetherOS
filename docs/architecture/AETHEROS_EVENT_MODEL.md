# AetherOS Event Model

Source: `kernel/event_bus.py` (`EventBus`, `Event`, `EventTopics`),
`kernel/core/types.py` (`KernelEvent`), `kernel/inter_agent.py` (legacy).

## EventBus

```python
class EventBus:
    def subscribe(topic: str, callback: Callable[[Event], None], priority=EventPriority.NORMAL) -> Subscription
    def emit(topic: str, data: Dict, source: str = "") -> int
    def shutdown()
```

- Wildcard subscriptions: `test.*`, `**` (global)
- Priority: `HIGH` → `NORMAL` → `LOW`
- Shutdown prevents further publication
- Per-subscription `cancel()`

## KernelEvent

Canonical envelope with full provenance and tracing:

```text
KernelEvent {
    event_id: str
    topic: str
    source: str
    agent_id: str
    process_id: str
    task_id: str
    intent_id: str
    trace_id: str
    span_id: str
    parent_span_id: str | null
    data: Dict
    provenance: ProvenanceType
    timestamp: float
    schema_version: "1.0"
}
```

## Core Topics (EventTopics)

```text
lifecycle.started / lifecycle.completed / lifecycle.failed
agent.created / agent.started / agent.ready / agent.paused / agent.resumed / agent.completed / agent.failed / agent.terminated
intent.created / intent.admitted / intent.denied
capability.pre_invoke / capability.post_invoke / capability.denied
task.created / task.started / task.completed / task.failed / task.cancelled
resource.allocated / resource.released / resource.exhausted
security.violation / security.emergency_stop / security.emergency_stop_cleared
policy.evaluated / policy.denied
approval.requested / approval.granted / approval.denied
checkpoint.created / checkpoint.restored
memory.read / memory.written
model.selected / model.failed
tool.called / tool.completed / tool.failed
browser.changed / computer.changed
capsule.created / capsule.started / capsule.paused / capsule.resumed / capsule.checkpoint / capsule.quarantined / capsule.destroyed / capsule.migrated
agent.handoff / agent.delegated
swarm.started / swarm.completed / swarm.failed
```

## Inter-Agent Bus (legacy)

`kernel/inter_agent.py` — `InterAgentBus`, `AgentMessage`,
`SharedMemoryEntry`, `TaskHandoff`. Not used by canonical kernel path
(capsules use hypervisor events). Retained for compatibility.

## Wildcards

- `test.*` matches `test.a`, `test.b`
- `**` matches everything (global subscription)
- Priority ordering: HIGH → NORMAL → LOW

## KernelEvent vs Event

`EventBus` uses lightweight `Event(topic, data, source, priority)`.
`KernelEvent` is the rich envelope emitted by kernel subsystems
(`event_bus.emit("topic", data)` creates `Event`, not `KernelEvent` —
`KernelEvent` is used by `ObservabilityEngine` for tracing).

## Schema Versioning

`KernelEvent.schema_version: "1.0"` — future versions will bump and
provide migrations. All events carry `timestamp`, `trace_id`, `span_id`,
`parent_span_id` for distributed tracing.