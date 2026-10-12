# AetherOS Memory Architecture

Two consolidated stores:

1. **Kernel MemoryManager** (`kernel/core/memory_manager.py`) — canonical
   provider registry + per-agent scoped namespaces (`agent:<id>:scope`).
   Scopes: `working`, `episodic`, `semantic`, `procedural`, `project`,
   `research`, `spatial`, `ambient`, `agent`, `swarm`, `shared`.

2. **Memory 2.0** (`aetheros_memory_intelligence/`) — Master 41 store of
   record. Exposed as kernel providers:
   - `MemoryOsProvider` (legacy `agent/memory_os`) → `IMemoryProvider`
   - `Memory2Provider` (Master 41 `MemoryService`) → `IMemoryProvider`

Both exposed via `kernel.memory_manager` with `register_provider(name,
provider, scopes)` and namespace isolation (`agent:<id>:scope`).

## Scopes

| Kernel Scope | Memory 2.0 RecordScope | Notes |
|---|---|---|
| working | session | turn buffer |
| episodic | session | |
| semantic | user | |
| procedural | user | |
| project | project | |
| research | research | |
| spatial | workspace | |
| ambient | session | |
| agent | agent | |
| swarm | task | |
| shared | global | |

Memory 2.0 scopes: `global`, `user`, `project`, `workspace`, `session`,
`task`, `agent`, `research`, `artifact`.

## Providers

```python
# Legacy
from kernel.core.memory_os_bridge import register_memory_os_provider
register_memory_os_provider(kernel)

# Memory 2.0 (Master 41)
from kernel.core.memory_os_bridge import register_memory2_provider
register_memory2_provider(kernel)
```

Both implement `IMemoryProvider`: `read(scope, key)`, `write(scope, key,
value)`, `search(scope, query, limit)`, `delete(scope, key)`.

## Provenance

Memory 2.0 records carry: `record_type` (14 types), `scope` (9 scopes),
`provenance` (10 kinds: `USER_STATED`, `SYSTEM`, `AGENT_INFERRED`,
`WEB_EXTRACTED`, `TOOL_OUTPUT`, `DEDUCIBLE`, `RESEARCH_EVIDENCE`,
`PROCEDURAL`, `PREFERENCE`, `ARTIFACT`), `confidence` (0-1), `ttl`,
`valid_from/until`, version chain (`supersedes/superseded_by`).

Kernel writes carry `provenance: {source_capsule, agent, task, confidence,
classification, origin: AGENT_DERIVED}`.

## Access Control

- Kernel namespaces are per-agent (`agent:<id>:scope`) — no cross-agent
  leakage without grant.
- Memory 2.0 enforces `explicit > inferred`, isolation rules
  (project/task scopes require same `project_id`), `allow_agents`,
  sensitivity (`INTERNAL/SENSITIVE/SECRET`).
- `SecretBroker` mediates secrets; raw values never in env or context.

## Persistence

- Kernel: in-memory + optional persistence via `StateManager` (SQLite
  + FTS5 for search)
- Memory 2.0: `RecordStore` (atomic JSON, FTS5 via `RecordStore`,
  O(n²) rewrite at scale — SQLite backend planned)
- Checkpoints snapshot `memory_refs` (keys) not raw values; restore
  rehydrates from providers.

## Research Integration

`research` scope + `evidence` mount → `research.search/fetch` syscalls
write to `research` scope as `WEB_DERIVED` provenance. Contradiction
analysis, citation, evidence store, synthesis, report artifact.