# AetherOS Execution Graph

## Overview

The Execution Graph defines how tasks are organized, ordered, and executed.
It supports sequential, parallel, conditional, dependent, retry, fallback,
and human-approval execution modes.

## Graph Structure

```python
{
    "nodes": [
        {"id": "task_a", "name": "Research", "status": "completed", "role": "research"},
        {"id": "task_b", "name": "Compare Pricing", "status": "running", "role": "data"},
    ],
    "edges": [
        {"from": "task_a", "to": "task_b"},
        {"from": "task_b", "to": "task_c"},
    ],
    "levels": [
        ["task_a", "task_d"],     # Level 0: parallel tasks
        ["task_b"],                # Level 1: depends on A, D
        ["task_c"],                # Level 2: depends on B
    ]
}
```

## Execution Modes

### Sequential
Tasks run one after another in dependency order.

```
Task A → Task B → Task C
```

### Parallel
Independent tasks run simultaneously.

```
Task A ──┐
         ├── Task C
Task B ──┘
```

### Conditional
Task execution depends on a condition being met.

```
Task A → [Condition] → Task B (if true)
                     → Task C (if false)
```

### Dependent
Task waits for all dependencies to complete.

```
Task A ──┐
         ├── Task C (waits for A AND B)
Task B ──┘
```

### Retry
Task automatically retries on failure.

```
Task A → (fail) → Retry 1 → (fail) → Retry 2 → (success)
```

### Fallback
Uses alternative model/agent on failure.

```
Task A (Model: GPT-4) → (fail) → Task A (Model: Claude) → (success)
```

### Human Approval
Pauses execution for user approval.

```
Task A → [Approval Required] → (approved) → Task B
                             → (denied) → Task C
```

## Level-Based Execution

The TaskOrchestrator organizes tasks into levels:

1. **Level 0** — Tasks with no dependencies (run in parallel)
2. **Level 1** — Tasks depending on Level 0
3. **Level 2** — Tasks depending on Level 1
4. **...**

Within each level:
- Tasks with `execution_mode = PARALLEL` run concurrently
- All other tasks run sequentially
- A task failure can stop the entire plan (configurable)

## Graph Construction

The `_build_execution_graph()` method in `TaskOrchestrator`:
1. Maps all tasks to nodes
2. Creates edges from dependencies
3. Computes topological levels
4. Returns complete graph structure

## Graph Visualization

The desktop UI renders the execution graph:
- Each task as a card with status indicator
- Dependency edges shown between tasks
- Color-coded by status (green=completed, blue=running, red=failed, gray=pending)
- Progress bars for running tasks
- Role badges and execution mode indicators

## Integration

The execution graph integrates with:
- **Checkpoint System** — State saved after each level
- **Approval System** — Human approval before sensitive tasks
- **Model Router** — Optimal model assigned per task
- **Recovery System** — Retry and fallback on failure
- **Monitoring** — Real-time progress tracking
