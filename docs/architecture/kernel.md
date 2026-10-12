# AetherOS Kernel Architecture

## Overview

The AetherOS Kernel is the **operating layer** of the AetherOS AI system. It is NOT an LLM and NOT a chatbot — it is the coordination layer that controls agents, memory, planning, execution, and communication.

The kernel wraps existing Aetheros infrastructure (AIAgent, tool registry, cron/scheduler, plugins, MCP) with a structured lifecycle, event-driven communication, and service-oriented architecture.

```
┌─────────────────────────────────────────────────────────────┐
│                     AetherOS Kernel                           │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Planner    │  │  Executor    │  │  State Manager   │  │
│  │  (Goal→DAG)  │  │  (Run/Tool)  │  │  (Persistence)   │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────────────┘  │
│         │                  │                                   │
│  ┌──────▼───────┐  ┌──────▼───────┐  ┌──────────────────┐  │
│  │  TaskGraph   │  │  Scheduler   │  │   Workspace      │  │
│  │  (DAG Model) │  │  (Jobs/Cron) │  │  (Sessions)      │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────────────┘  │
│         │                  │                                   │
│  ┌──────▼───────┐  ┌──────▼───────┐  ┌──────────────────┐  │
│  │   Registry   │  │   Event Bus  │  │  Permissions     │  │
│  │  (Discovery) │  │  (Pub/Sub)   │  │  (Security)      │  │
│  └──────┬───────┘  └──────────────┘  └──────────────────┘  │
│         │                                                     │
│  ┌──────▼───────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Context    │  │  Telemetry   │  │  Lifecycle       │  │
│  │  (Sharing)   │  │  (Metrics)   │  │  (Start/Stop)    │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐                           │
│  │    Router    │  │  Kernel      │                           │
│  │  (Dispatch)  │  │  (Bootstrap) │                           │
│  └──────────────┘  └──────────────┘                           │
└─────────────────────────────────────────────────────────────┘
            │                      │
            ▼                      ▼
┌───────────────────────┐  ┌──────────────────────┐
│  Existing Aetheros    │  │  External Systems    │
│  Infrastructure:      │  │  - LLM Providers     │
│  - AIAgent            │  │  - MCP Servers       │
│  - Tool Registry      │  │  - Sandboxes         │
│  - Cron/Scheduler     │  │  - Network           │
│  - SessionDB          │  │  - Browser           │
│  - Plugins            │  └──────────────────────┘
│  - Memory Providers   │
│  - Context Engines    │
└───────────────────────┘
```

## Design Principles

1. **No tight coupling** — All subsystems communicate through the Event Bus
2. **Single responsibility** — Each module has one job, and does it well
3. **Backward compatibility** — The kernel wraps existing infrastructure, never replaces it
4. **Interfaces everywhere** — All modules define clear ABC-like interfaces
5. **No circular imports** — Dependencies flow in one direction (bottom → top)
6. **Dependency injection** — Services receive their dependencies through constructors
7. **Type hints throughout** — All public APIs are fully typed
8. **Crash resilience** — State persistence enables recovery from failures

## Module Responsibilities

### Core Infrastructure

| Module | Responsibility |
|--------|---------------|
| `kernel.py` | Kernel bootstrap, configuration, lifecycle orchestration |
| `lifecycle.py` | Component startup order, health checks, graceful shutdown |
| `event_bus.py` | Pub/sub event system — the nervous system of the kernel |
| `registry.py` | Service discovery — tools, agents, plugins, MCP servers |

### Execution Services

| Module | Responsibility |
|--------|---------------|
| `planner.py` | Goal decomposition → execution plan → task graph |
| `executor.py` | Run AIAgent conversations, execute tools, retry logic |
| `scheduler.py` | Background jobs, periodic tasks, cron integration |
| `task_graph.py` | DAG representation of tasks with dependencies |

### Management Services

| Module | Responsibility |
|--------|---------------|
| `workspace.py` | Project directories, temp sessions, artifacts |
| `context.py` | Shared context namespaces across agents |
| `permissions.py` | Centralized permission checking |
| `router.py` | Request routing to handlers by pattern matching |

### Observability Services

| Module | Responsibility |
|--------|---------------|
| `telemetry.py` | Metrics collection (vendor-agnostic) |
| `state_manager.py` | State persistence, crash recovery, checkpoints |

## Data Flow

### User Request Flow

```
User Goal
    │
    ▼
Planner.create_plan(goal)          ──▶ emit "task.created"
    │
    ▼
Plan approved / steps ready
    │
    ▼
Executor.run_agent(agent, step)    ──▶ emit "agent.started"
    │
    ▼
Agent executes (tool calls)        ──▶ emit "tool.started" / "tool.completed"
    │
    ▼
Result collected                   ──▶ emit "task.progress"
    │
    ▼
Next step / plan complete          ──▶ emit "task.completed"
```

### Event Flow

```
Component A ──▶ EventBus.publish(event)
                     │
                     ├──▶ Component B (subscriber)
                     ├──▶ Component C (subscriber)
                     ├──▶ TelemetryCollector (error tracking)
                     └──▶ StateManager (state update)
```

### Scheduler Flow

```
KernelScheduler.tick()
    │
    ├──▶ Check due interval/oneshot jobs
    ├──▶ Execute job callbacks
    ├──▶ Emit "scheduler.job_started" / "job_completed"
    └──▶ Delegate cron jobs to existing cron/scheduler.py
```

## Lifecycle

```
Kernel.boot()
    │
    ├── 1. Register services with LifecycleManager
    ├── 2. Wire event bus listeners
    ├── 3. Start all lifecycle services (dependency-ordered)
    ├── 4. Discover components (tools, plugins, MCP)
    ├── 5. Load persisted state
    ├── 6. Start scheduler
    ├── 7. Install signal handlers
    └── 8. Emit "lifecycle.started"

Kernel.shutdown()
    │
    ├── 1. Emit "system.shutdown"
    ├── 2. Stop state save timer
    ├── 3. Persist state (final)
    ├── 4. Stop scheduler
    ├── 5. Clean up workspace sessions
    ├── 6. Stop all lifecycle services (reverse order)
    └── 7. Shut down event bus
```

## Extension Guide

### Adding a New Kernel Module

1. Create `kernel/your_module.py` with a class that takes `Optional[EventBus]`
2. Register it in `Kernel.__init__()` as an optional service
3. Add a `ServiceRegistration` in `Kernel._register_core_services()`
4. Export the class from `kernel/__init__.py`

### Using the Kernel from Existing Code

```python
from kernel import Kernel

# Create and boot the kernel
kernel = Kernel()
kernel.boot()

# Access services
plan = kernel.planner.create_plan("Deploy the application")
result = kernel.executor.run_agent(agent, "Build")

# Shut down
kernel.shutdown()
```

### Subscribing to Events

```python
kernel.event_bus.subscribe("agent.started", my_handler)
kernel.event_bus.subscribe("**", catch_all_handler)  # Wildcard
sub = kernel.event_bus.subscribe("tool.*", tool_handler)
sub.cancel()  # Unsubscribe
```

### Custom Permission Rules

```python
kernel.permissions.add_rule(PermissionRule(
    name="block-temp-dir",
    action=PermissionAction.WRITE_FILE,
    level=PermissionLevel.DENY,
    target_pattern="/tmp/**",
))
```

## Backward Compatibility

The kernel runs alongside existing Aetheros infrastructure without conflicts:

- **AIAgent** — Used by `Executor.run_agent()`; the kernel does NOT replace it
- **Tool Registry** — Discovered by `AgentRegistry.discover_from_tool_registry()`
- **Cron** — `KernelScheduler.add_existing_cron_jobs()` imports cron jobs
- **Plugins** — Discovered via existing plugin system
- **File Safety** — `PermissionManager.integrate_file_safety()` imports rules
- **SessionDB** — `StateManager.integrate_session_db()` connects for state querying
