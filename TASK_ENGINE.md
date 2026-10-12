# AetherOS Task Engine

## Overview

The Task Engine manages the complete lifecycle of autonomous task execution,
from initial decomposition through parallel execution, failure recovery, and
result validation.

## Task Lifecycle

```
PENDING → RUNNING → COMPLETED
                   → FAILED → (RETRY → RUNNING → COMPLETED/FAILED)
                   → BLOCKED → (APPROVED → RUNNING)
                             → (DENIED → CANCELLED)
         → CANCELLED
         → PAUSED → (RESUMED → RUNNING)
```

## Task Types

### OrchestrationTask
```python
@dataclass
class OrchestrationTask:
    id: str
    name: str
    description: str
    agent_role: AgentRole
    model: str
    provider: str
    tools: list[str]
    dependencies: list[str]
    execution_mode: GraphExecutionMode
    status: TaskStatus
    progress: float
    result: Any
    error: str
    retry_count: int
    max_retries: int
    requires_approval: bool
    approval_actions: list[ApprovalAction]
    estimated_duration: float
    actual_duration: float
    cost: float
```

### OrchestrationPlan
```python
@dataclass
class OrchestrationPlan:
    id: str
    goal: str
    description: str
    subtasks: list[OrchestrationTask]
    dependencies: dict[str, list[str]]
    required_tools: list[str]
    required_agents: list[AgentRole]
    required_permissions: list[str]
    estimated_cost: float
    estimated_time: float
    risk_level: RiskLevel
    execution_graph: dict
```

## Execution Graph

The execution graph organizes tasks into dependency levels:

```
Level 0: Task A, Task B    (no dependencies, parallel)
             │      │
Level 1:     Task C         (depends on A, B)
             │
Level 2:     Task D         (depends on C)
```

### Graph Structure
```python
{
    "nodes": [{"id": "task_a", "name": "...", "status": "...", "role": "..."}],
    "edges": [{"from": "task_a", "to": "task_c"}],
    "levels": [["task_a", "task_b"], ["task_c"], ["task_d"]]
}
```

## Task Planning

The TaskPlanner (`aetheros_automation/tasks/planner.py`) decomposes goals:

1. Parse goal into sentences/segments
2. Assign agent roles based on keywords
3. Create sequential dependencies
4. Estimate durations
5. Assign required tools

### NLPAutomationEngine (`aetheros_automation/nlp/nlp_automation.py`)

Natural language processing for automation:
- Parse complex requests into tasks
- Infer agent roles from text
- Detect scheduling patterns ("every Monday")
- Assess risk levels
- Extract required tools

## Task Templates

Built-in templates (`aetheros_automation/templates/templates.py`):

| Template | Description |
|----------|-------------|
| research_report | Research topic, collect data, generate report |
| software_development | Plan, implement, test, deploy |
| data_analysis | Load, clean, analyze, visualize, report |
| content_creation | Research, outline, write, create visuals |
| email_campaign | Plan, write, review, send |
| business_automation | Analyze, design, implement, test, deploy |
| personal_assistant | Understand, gather, execute, confirm |

## Missions (`aetheros_jarvis/mission.py`)

A mission turns a user goal into a plan, attaches concrete steps, requests
approval when required, and executes each step through the orchestrator.

```bash
aetheros mission create "ship v2"      # draft
aetheros mission plan <id> "step one" "step two"
aetheros mission approve <id>
aetheros mission run <id>
aetheros mission show <id>             # final report
```

Also available in the interactive CLI and messaging gateway as `/mission …`.

Flow:
- `create()` — a draft ``MissionPlan`` (approval required by default).
- `plan()` — attach concrete steps; plan enters ``awaiting_approval``.
- `approve()` — approves or cancels the plan.
- `execute()` — runs each step through the real ``AgentExecutionEngine``
  (via ``TaskOrchestrator``) when no custom step executor is installed.
  Steps that require approval are authorized through the security facade.

The async orchestrator ``run()`` is bridged from the synchronous
``MissionManager.execute()`` without corrupting any running event loop
(``asyncio.run`` when no loop is active, otherwise a dedicated worker thread).

## Validation

The ResultValidator ensures task completeness:

- Result not None
- Has summary field
- Relevance check against task description
- File existence check (when required)
- Custom validators

## Limits and Guards

```python
limits = {
    "max_steps": 100,
    "max_time": 3600,
    "max_cost": 10.0,
    "max_tokens": 1000000,
    "max_sub_agents": 10,
    "max_parallel_tasks": 5,
    "max_tool_calls": 500,
}
```
