# AetherOS Context Engine

Source: `kernel/core/context_manager.py`, `kernel/core/hypervisor/hypervisor.py`.

## ContextManager

```python
class ContextManager:
    def create_namespace(namespace: str) -> ContextNamespace
    def get_namespace(namespace: str) -> ContextNamespace | None
    def set_context(namespace: str, key: str, value: Any, ttl_seconds: float = None) -> None
    def get_context(namespace: str, key: str) -> Any
    def delete_context(namespace: str, key: str) -> bool
    def list_keys(namespace: str) -> List[str]
    def get_all_context() -> Dict[str, Dict]
    def scoped(namespace: str) -> ContextScope  # context manager
    def prune_expired() -> int
```

## Namespaces

Logical isolation per conversation/task/agent. Examples:
- `conversation:<id>`
- `task:<task_id>`
- `agent:<agent_id>`
- `capsule:<capsule_id>`
- `system`

## Context Classes (§14)

```text
CRITICAL    // never evicted
HIGH        // user intent, active task state
NORMAL      // tool outputs, intermediate results
LOW         // historical, reference
EPHEMERAL   // scratch, TTL-managed
DERIVED     // inferred, synthesized
UNTRUSTED   // web, OCR, external
SENSITIVE   // private/secret data
PRIVATE     // user private
PUBLIC      // public data
```

Untrusted external content never silently becomes authoritative context.

## Budget + Eviction

- Token budget per namespace (`context_budget` from profile)
- LRU eviction of NON-CRITICAL when over budget
- TTL expiry (`prune_expired()`)
- Compression strategies (registered callbacks) for large contexts

## Capsule Integration

Capsule `memory_scope` maps to a namespace (e.g., `agent:<id>`,
`task:<id>`, `project:<id>`). Capsules cannot inherit context across
boundaries without explicit grant. `invoke()` redacts screen inputs
before they enter context.