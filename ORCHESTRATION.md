# AetherOS Orchestration System

## Overview

The AetherOS Orchestration System provides autonomous task decomposition,
planning, execution, and monitoring. It transforms complex user requests
into executable plans with multi-agent collaboration, parallel execution,
failure recovery, and human-in-the-loop approval.

## Architecture

```
User Request
    │
    ▼
TaskOrchestrator
    │
    ├── understand_objective()  →  Parse & analyze
    ├── create_execution_plan() →  Decompose into subtasks
    ├── select_agent()          →  Assign agent + model
    ├── execute_plan()          →  Run execution graph
    └── monitor & recover       →  Retry, fallback, checkpoint
```

## Key Components

### TaskOrchestrator (`aetheros_automation/orchestrator/orchestrator.py`)

Central class managing the full lifecycle:
- `understand_objective()` — Parse user request
- `create_execution_plan()` — Decompose into subtasks with dependencies
- `select_agent()` — Choose best agent + model for each task
- `execute_plan()` — Run the execution graph
- `pause/resume/cancel/restart` — Lifecycle control
- `retry_failed_tasks()` — Recover from failures

### ExecutionEngine (`aetheros_automation/orchestrator/execution_engine.py`)

Runs individual tasks with tool execution:
- `execute_task()` — Execute a single orchestration task
- `_call_tool()` — Delegate to tool registry or automation tools

### AgentExecutionEngine (`aetheros_automation/orchestrator/agent_engine.py`)

Production execution engine that spawns a real ``AIAgent`` per task (the
legacy ``ExecutionEngine`` simulated tool calls).  Drop-in compatible with
``TaskOrchestrator(execution_engine=...)``:

```python
from aetheros_automation.orchestrator import AgentExecutionEngine, TaskOrchestrator

orchestrator = TaskOrchestrator(execution_engine=AgentExecutionEngine())
```

Behavior:
- Constructs a headless, cron-style ``AIAgent`` per task via the configured
  runtime provider (``aetheros_cli.runtime_provider``) with an isolated
  system prompt built from the task/agent/context.
- Runs ``run_conversation()`` under a hard timeout (default 600s) in a
  worker thread; on timeout the child agent is interrupted.
- Returns the ``result_data`` shape the orchestrator validator accepts
  (``task_id``, ``summary``, ``status``, ``duration``, ``api_calls``).
- Emits ``tool.called`` / ``tool.completed`` events and records execution
  contexts for observability.
- Headless-safe: installs a non-interactive approval callback so subagent
  runs never fall back to ``input()``.

### Security integration (`aetheros_automation/orchestrator/security.py`)

Thin facade over :mod:`aetheros_security`.  Mission/orchestrator steps are
authorized through the central authorization engine, agent identities are
registered with the identity registry, and the mission lifecycle (create /
approve / execute / finish) is audited.  Enforcement is feature-preserving:
an explicit deny rule, emergency stop, or lockdown blocks a step, while the
default posture stays permissive because the mission's own approval flow is
the primary human gate.

### CheckpointManager (`aetheros_automation/orchestrator/checkpoint.py`)

Persists execution state for pause/resume/recovery:
- `save_checkpoint()` — Save state after each task
- `load_checkpoint()` — Restore from checkpoint
- `list_checkpoints()` — Browse available checkpoints
- `restore_state()` — Recover execution state

### ModelRouter (`aetheros_automation/routing/model_router.py`)

Automatic model selection based on task type:
- `select_model()` — Choose best model for task type
- `get_fallback()` — Get fallback model when primary fails
- Role-based preferences (developer → claude-sonnet, research → gpt-4o, etc.)

### RetryHandler (`aetheros_automation/recovery/retry.py`)

Failure recovery with exponential backoff:
- `execute_with_retry()` — Retry operation with backoff
- `get_backoff()` — Calculate exponential backoff with jitter
- `classify_failure()` — Categorize failure type

### FallbackHandler (`aetheros_automation/recovery/fallback.py`)

Fallback chain execution:
- `execute_with_fallback()` — Try primary, then fallbacks
- `execute_fallback_chain()` — Execute operations in sequence

### ResultValidator (`aetheros_automation/validation/validator.py`)

Validates task results before marking complete:
- `validate()` — Check result completeness and relevance
- File existence checks, data integrity checks

## Execution Modes

- **Sequential** — Tasks run one after another
- **Parallel** — Independent tasks run simultaneously
- **Dependent** — Task waits for dependencies to complete
- **Conditional** — Task execution depends on conditions
- **Retry** — Task retries on failure
- **Fallback** — Uses alternative on failure
- **Human Approval** — Requires user approval before execution

## Agent Roles

| Role | Description | Tools |
|------|-------------|-------|
| planner | Strategic planning | Coordination |
| developer | Code development | code_execution, terminal, file_ops |
| browser | Web browsing | browser_navigate |
| research | Information gathering | web_search, browser |
| writer | Content creation | file_operations |
| qa | Testing & validation | code_execution |
| deployment | Release management | terminal |
| security | Security analysis | audit tools |
| creative | Design & generation | image_gen |
| data | Data analysis | code_execution, data_analysis |
| communication | Messaging | send_message |
| review | Quality review | review tools |
| coordinator | Task coordination | delegation |

## Checkpoint System

Checkpoints are automatically created after each task completes:
- Saved to `~/.aetheros/automation/checkpoints/<plan_id>/`
- Track completed/failed/pending tasks
- Support pause, resume, cancel, restart
- Can restore from any checkpoint

## Security Integration

Every agent and task uses:
- Permission System — Granular access control
- Approval System — Human-in-the-loop for sensitive actions
- Sandbox — Isolated execution environment
- Credential Vault — Secure credential storage
- Audit Log — Complete action history
