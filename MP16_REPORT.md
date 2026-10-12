# MP16 — Multi-Agent Orchestration + Autonomous Mission Engine

## Status: SHIPPED

Real-agent execution for the orchestrator, a production mission engine, full
CLI/gateway/slash integration, and zero-trust security wiring.

## What Was Built

### 1. Real Agent Execution (`aetheros_automation/orchestrator/agent_engine.py`)

The orchestrator previously ran each task through `ExecutionEngine`, which
**simulated** tool calls. `AgentExecutionEngine` is a drop-in replacement that
spawns a **real** headless `AIAgent` per task:

- Constructs a cron-style headless `AIAgent` via `aetheros_cli.runtime_provider`
  (`resolve_runtime_provider` → provider, api_key, base_url, api_mode, acp).
- Builds an isolated, deterministic system prompt per task/agent/context.
- Runs `run_conversation()` under a hard timeout (default 600s) in a worker
  thread; interrupts the child on timeout.
- Returns the `result_data` shape the orchestrator validator accepts
  (`task_id`, `task_name`, `agent_id`, `agent_role`, `model`, `provider`,
  `result.summary`, `summary`, `status`, `duration`, `api_calls`).
- Emits `tool.called` / `tool.completed` events; records execution contexts.
- Headless-safe: installs a non-interactive approval callback
  (`tools.terminal_tool.set_approval_callback`) so subagents never deadlock
  on `input()`.
- Agent constructor and run loop are injectable for hermetic tests.

```python
orchestrator = TaskOrchestrator(execution_engine=AgentExecutionEngine())
```

### 2. Mission Engine (`aetheros_jarvis/mission.py`)

`MissionManager` drives the full lifecycle: `create(goal) → plan(steps) →
approve() → execute() → report()`. Each step executes through the real
orchestrator when no custom step executor is installed. The async
`TaskOrchestrator.run()` is awaited from the synchronous API without
corrupting any running event loop (`asyncio.run` when no loop is active;
otherwise a dedicated worker-thread loop).

### 3. `aetheros mission` CLI + Slash Command + Gateway

- `aetheros_cli/missions.py` — `create | list | show | plan | approve | run`.
- Wired into `aetheros_cli/main.py` (argparse), `cli.py` + `cli_commands_mixin.py`
  (interactive `/mission`), `aetheros_cli/commands.py` (registry), and
  `gateway/run.py` + `gateway/slash_commands.py` (messaging `/mission`).
- Command registry automatically feeds help, autocomplete, Telegram menu, and
  Slack routing. The manager is a process-global singleton so create→plan→run
  persists across invocations within a process.

### 4. Security Integration (`aetheros_automation/orchestrator/security.py`)

Thin defensive facade over `aetheros_security`:

- Mission steps are authorized through the central authorization engine.
- Agent identities are registered with the identity registry.
- The mission lifecycle (create / approve / execute / finish) is audited.

**Feature-preserving enforcement:** the mission's own approval flow is the
primary human gate. A step is blocked only on an *explicit* security signal —
a deny rule, emergency stop, or lockdown. The engine's default-deny fallback
(no policy configured) does NOT block, so missions work out of the box.

### 5. Profile-Safe Paths

- `checkpoint.py` — checkpoint base dir uses `get_aetheros_home()`.
- `orchestrator/store.py` — storage dir via `get_aetheros_home()`.
- `orchestrator.py` — orchestrations dir via `get_aetheros_home()`.
- Never hardcoded `~/.aetheros`; each profile gets isolated state.

## Files Touched

| File | Change |
|------|--------|
| `aetheros_automation/orchestrator/agent_engine.py` | New — real agent engine |
| `aetheros_automation/orchestrator/security.py` | New — security facade |
| `aetheros_automation/orchestrator/__init__.py` | Export `AgentExecutionEngine` |
| `aetheros_jarvis/mission.py` | Orchestrator bridge + async helper + security |
| `aetheros_cli/missions.py` | New — mission CLI + slash |
| `aetheros_cli/main.py`, `cli.py`, `cli_commands_mixin.py` | Wire mission command |
| `aetheros_cli/commands.py` | `CommandDef("mission", ...)` |
| `gateway/run.py`, `gateway/slash_commands.py` | Gateway `/mission` handler |
| `aetheros_automation/orchestrator/checkpoint.py` | Profile-safe path |
| `aetheros_automation/orchestrator/store.py` | Profile-safe path |
| `aetheros_automation/orchestrator/orchestrator.py` | Profile-safe path |
| `ORCHESTRATION.md`, `TASK_ENGINE.md` | Docs |

## Tests

- `tests/aetheros_automation/test_agent_engine.py` — 21 tests (execution,
  validator compat, hard timeout, events, orchestrator plug-in, system prompt,
  mission bridge, loop bridge, profile-safe paths, security integration).
- `tests/aetheros_cli/test_missions_cli.py` — 8 tests (create/plan/run flow,
  unknown mission, missing args, slash help/full flow).
- Regression: `tests/aetheros_automation/` + `tests/jarvis/` → **428 passed**.
- Security: `tests/security/` → **193 passed**.
- Gateway slash dispatch → **39 passed**.

**Pre-existing, unrelated failures** (not introduced by MP16):
`tests/aetheros_cli/test_commands.py` — the `knowledge` command carries alias
`memory` which shadows the canonical `memory` command
(`aetheros_cli/commands.py:118-119`). Touching that registry predates this
work.

## Known Gaps / Follow-ups

- Scheduling (cron-style missions), budgets/cost routing, and pause/resume at
  the mission level reuse existing `cron/` / `checkpoints` infrastructure and
  were not re-implemented (per the "extend, don't duplicate" rule).
- A mission UI surface in the TUI/dashboard is a candidate follow-up.