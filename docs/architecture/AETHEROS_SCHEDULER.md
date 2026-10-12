# AetherOS Scheduler + Resource Model

Source: `kernel/core/scheduler.py`, `kernel/core/resource_manager.py`.

## Scheduler (`KernelScheduler`)

OS-like scheduler for agent processes.

### Dimensions

- Priority class: `INTERACTIVE`, `REAL_TIME`, `HIGH_PRIORITY`, `NORMAL`,
  `BACKGROUND`, `BATCH`, `MAINTENANCE`, `RESEARCH`, `AUTOMATION`, `PHYSICAL`
- Deadline awareness
- Resource availability
- Dependency graph
- Fairness / starvation prevention
- Interactive vs background
- Autonomy level
- Battery/thermal state
- Privacy mode

### Priority ordering

Heap key: `(priority_class_rank, deadline, created_at, seq)`. Monotonic
`seq` ensures deterministic ordering for equal keys (fixes Master 58
`TypeError: '<' not supported` on tied keys).

### Operations

- `admit(process)`: CREATED→ADMITTED, push into priority queue
- `schedule(process)`: pop highest-priority ready agent, check resources,
  move to `_running`, emit `scheduler.scheduled`
- `preempt(agent_id)`: running→READY, re-queue, `stats["preempted"]++`
- `yield_cpu(agent_id)`: voluntary yield, running→READY, re-queue
- `block(agent_id, reason)`: running→BLOCKED, move to `_blocked`
- `unblock(agent_id)`: BLOCKED→READY, re-queue
- `complete(agent_id)`: running→COMPLETED, release resources, `stats["completed"]++`

### Starvation prevention

- Background agents never starve interactive: priority classes ordered
  `INTERACTIVE → REAL_TIME → HIGH → NORMAL → BACKGROUND → BATCH`
- `_check_starvation()`: agents in `BACKGROUND/BATCH/MAINTENANCE` waiting
  > 5 minutes get boosted one priority level (`_stats["starvation_events"]++`)

### Multi-agent (§12, §41)

Parent/child, swarms, DAG dependencies, parallel tasks, shared
artifacts, handoffs, deadlines, cancellation, failure propagation.
Swarm = scheduled workload with quotas, not uncontrolled collection of
LLM calls.

## Resource Model

`ResourceBudget` dimensions:
```
cpu_cores, gpu_memory_mb, ram_mb, disk_mb, network_mbps,
llm_tokens_per_minute, model_concurrency, tool_concurrency,
browser_sessions, computer_sessions, device_sessions,
research_requests_per_minute, agent_slots, automation_slots,
battery_percent, thermal_budget_celsius
```

### Lifecycle

```
reserve (admission) → allocate (spawn) → update_usage (runtime)
→ release (complete/fail/cancel) → checkpoint (optional)
```

- `reserve()` at admission (IntentManager → AuthorityManager.resource_manager)
- `allocate()` at spawn (AgentKernel.create_agent_process)
- `update_usage()` called by runtime during execution
- `release()` on complete/fail/cancel/shutdown
- `check_availability()` names the limiting resource on denial

### Scheduling classes (§52)

```
HARD_REAL_TIME → SOFT_REAL_TIME → INTERACTIVE → DELAY_TOLERANT → BATCH
```

### Profiles (§6)

Lean by default: scarce sessions requested only by profiles that need
them (browser→1, computer_use→1, physical/ambient→1, automation→1
automation slot). Profiles request only what they need (deny-by-default
footprint).

### GPU / NPU (§27)

Accounting only — `gpu_status()` returns `NOT_SUPPORTED` with
`detail: "No GPU time-slicing/memory enforcement is wired to capsules on
this host; GPU budgets are accounting-only."` No time-slicing or memory
enforcement claimed.