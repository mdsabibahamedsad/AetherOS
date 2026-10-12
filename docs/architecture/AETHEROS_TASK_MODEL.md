# AetherOS Task Model

Source: `kernel/core/task_manager.py` (canonical), `kernel.task_graph` (legacy DAGs),
`aetheros_automation/tasks` (legacy), `kernel/core/task_adapter.py` (migration).

## Canonical Task Lifecycle (canonical)

```
CREATED → QUEUED → PLANNING → READY → RUNNING
                          ↓
                      WAITING ↔ RUNNING
                          ↓
                      BLOCKED ↔ RUNNING
                          ↓
                      VERIFYING → COMPLETED | FAILED
                          ↓
                      PAUSED ↔ RUNNING
                          ↓
                      CANCELLED | EXPIRED | QUARANTINED
```

States: `pending`, `queued`, `planning`, `ready`, `running`, `waiting`,
`blocked`, `verifying`, `completed`, `failed`, `cancelled`, `paused`,
`requires_approval`.

Fields: `task_id`, `parent_task_id`, `root_task_id`, `agent_id`,
`intent_id`, `goal`, `description`, `constraints`, `success_criteria`,
`required_capabilities`, `status`, `priority`, `depends_on`, `blocks`,
`result`, `error`, `artifacts`, `created_at`, `updated_at`,
`started_at`, `completed_at`, `metadata`.

## Migration (§6, §47)

Legacy DAGs (`kernel.task_graph.TaskGraph`, `aetheros_automation/tasks`,
`core/jarvis`, `agent/orchestration`) are NOT rewritten. The adapter
`kernel/core/task_adapter.py` migrates a graph into canonical tasks:

```python
from kernel.core.task_adapter import import_graph
tasks = import_graph(graph, task_manager, agent_id, intent_id)
```

- Status mapping: `pending`→`pending`, `ready`→`ready`, `running`→`running`,
  `completed`→`completed`, `failed`→`failed`, `cancelled`→`cancelled`,
  `blocked`→`blocked`, `skipped`→`cancelled`
- Dependencies preserved via `depends_on` (resolved through
  `graph.get_dependencies(node_id)`)
- Node retry budgets, results, errors carried over
- Provenance records migration source (`metadata["migrated_from"]`,
  `metadata["legacy_node_id"]`)

## TaskManager integration

`TaskManager` lives in `kernel.core.task_manager` and is the canonical
task authority for the kernel path. It owns:
- `create_task(agent_id, intent_id, goal, ...)` → Task
- `get_task(task_id)` / `get_agent_tasks(agent_id)` / `get_ready_tasks()`
- `update_task_status(task_id, status, error)` / `set_task_result()`
- `get_task_tree(root_task_id)` → hierarchical view with children
- `build_tree(task_id)` → builds tree from flat tasks (children = reverse
  `depends_on`)

## Delegation

Child tasks created via `agent.spawn` / `agent.delegate` syscalls create
new `AgentProcess` with delegated authority subset (enforced by
`AuthorityManager.delegate_authority`). Parent task is `parent_task_id`;
child task tracks `root_task_id` for swarm-level budgeting.

## Scheduling integration

`KernelScheduler` admits `AgentProcess` (not tasks directly); the
agent's runtime pulls ready tasks via `TaskManager.get_ready_tasks()`.
Preemption, priority inheritance, deadlock detection, starvation boost
operate at the agent level.