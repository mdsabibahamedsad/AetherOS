# AetherOS Multi-Agent Swarm & Orchestration System

## Overview

The AetherOS Swarm System enables multiple specialized AI agents to work together on the same goal. It is an **optional orchestration layer** that sits on top of the [AetherOS Kernel](kernel.md) — the existing single-agent execution model works unchanged.

When a user submits a high-level objective, the swarm system automatically:
1. Analyzes the objective
2. Breaks it into tasks
3. Assigns tasks to specialized agents
4. Executes tasks concurrently when possible
5. Merges results
6. Produces a final answer

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      SwarmOrchestrator                                │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                   Workflow Pipeline                              │ │
│  │                                                                   │ │
│  │  Goal → SwarmPlanner → TaskAllocator → TaskDispatcher            │ │
│  │                    → Coordinator → ResultMerger → Output          │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ AgentRegistry│  │CapabilityReg │  │ InterAgentMessageBus     │  │
│  │ (13 builtins)│  │ (16 standard)│  │ (pub/sub messaging)      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
│                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ ConsensusEng │  │ConflictResolv│  │ ExecutionMonitor         │  │
│  │ (voting)     │  │ (locks/dup)  │  │ (progress events)        │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
│                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ SwarmWorker  │  │SwarmScheduler│  │ ProgressTracker          │  │
│  │ (agent exec) │  │ (dependency) │  │ (structured events)      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      AetherOS Kernel                                 │
│  EventBus │ KernelScheduler │ Planner │ Executor │ Registry          │
│  WorkspaceManager │ ContextManager │ PermissionManager │ Router       │
└─────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                Existing Aetheros Components                          │
│  AIAgent (single agent) │ Tool Registry │ Cron/Scheduler │ SessionDB │
│  Plugins │ MCP Servers │ Memory Providers │ Context Engines          │
└─────────────────────────────────────────────────────────────────────┘
```

## Module Responsibilities

### Orchestration Layer

| Module | Responsibility |
|--------|---------------|
| `orchestrator.py` | Swarm lifecycle (start/stop), workflow entry point, health, subsystem access |
| `coordinator.py` | Workflow state machine, orchestrates plan→execute→merge pipeline |
| `planner.py` | Goal decomposition into agent tasks with capability requirements |
| `dispatcher.py` | Task scheduling and execution across agent types |
| `scheduler.py` | Dependency-aware parallel execution with retries |

### Agent Management

| Module | Responsibility |
|--------|---------------|
| `registry.py` | Agent type profiles (13 built-in types with capabilities, cost, speed) |
| `capabilities.py` | Capability definitions (16 standard capabilities) |
| `worker.py` | Agent execution via delegate_task / kernel executor |
| `task_allocator.py` | Capability+workload-based task-to-agent assignment |

### Communication & Consensus

| Module | Responsibility |
|--------|---------------|
| `communication.py` | Inter-agent message bus (requests, responses, broadcast) |
| `consensus.py` | Weighted voting for disagreeing agents |
| `conflict_resolution.py` | File/tool/workspace lock management, duplicate detection |

### Observability

| Module | Responsibility |
|--------|---------------|
| `execution_monitor.py` | Per-task progress tracking and structured reports |
| `progress_tracker.py` | Fine-grained event emission for UI/CLI |
| `result_merger.py` | Output deduplication, text merging, summary extraction |

## Agent Types

13 built-in agent types are registered on swarm startup:

| Agent | Capabilities | Cost | Speed | Best For |
|-------|-------------|------|-------|----------|
| `planning-agent` | planning, analysis, decomposition | 15 | 4/10 | Analyzing goals, creating plans |
| `coding-agent` | coding, code_review, refactoring | 20 | 5/10 | Writing and editing code |
| `research-agent` | research, web_search, analysis | 10 | 4/10 | Web research, gathering info |
| `browser-agent` | browser, web_interaction | 15 | 6/10 | Browser-based interactions |
| `filesystem-agent` | filesystem, file_ops | 5 | 2/10 | File management operations |
| `terminal-agent` | terminal, execution, build | 5 | 2/10 | Shell commands, builds |
| `documentation-agent` | documentation, writing | 10 | 4/10 | Generating docs and READMEs |
| `testing-agent` | testing, validation | 15 | 5/10 | Writing and running tests |
| `review-agent` | review, quality, audit | 15 | 5/10 | Code review, quality checks |
| `debug-agent` | debug, troubleshooting | 15 | 6/10 | Bug diagnosis and fixes |
| `memory-agent` | memory, recall, storage | 5 | 3/10 | Memory management |
| `plugin-agent` | plugin, custom | 10 | 5/10 | Plugin-managed capabilities |
| `mcp-agent` | mcp, external | 10 | 5/10 | MCP server delegation |

## Data Flow

### Goal Execution Flow

```
User submits goal: "Build a web app with user authentication"
    │
    ▼
1. SwarmOrchestrator.run_workflow(goal)
    │
    ▼
2. Coordinator.run_goal(goal)
    │
    ▼
3. SwarmPlanner.decompose_goal(goal)
   ├── Creates SwarmPlan with 5 AgentTasks:
   │   - [planning] Analyze goal and create execution plan
   │   - [research] Research relevant technologies
   │   - [coding]   Implement the solution
   │   - [testing]  Test the implementation
   │   - [review]   Review and finalize
   │
   ▼
4. TaskAllocator.find_best_agent(task, plan)
   ├── Evaluates registry by required capabilities
   ├── Scores based on: match %, workload, speed, cost
   └── Produces Assignment with confidence score
    │
    ▼
5. TaskDispatcher.dispatch_tasks(plan)
   ├── Runs ready tasks in parallel (max_concurrent)
   ├── Waits for dependencies before running dependents
   └── Collects results from each agent
    │
    ▼
6. AgentWorker.run_agent(goal, agent_type)
   ├── Spawns subagent via delegate_task / kernel executor
   ├── Monitors execution with timeout
   └── Returns AgentResult with output
    │
    ▼
7. ResultMerger.merge(completed_tasks, goal)
   ├── Deduplicates overlapping outputs
   ├── Orders contributions logically
   ├── Extracts summaries
   └── Produces coherent final result
    │
    ▼
8. Final output returned to user
```

### Failure Recovery Flow

```
Task fails (error/timeout)
    │
    ▼
Check retry budget (max_retries)
    │
    ├── Retries available → Re-execute on same or different agent type
    │
    └── No retries → Mark task as failed
         │
         ▼
    Coordinator checks if plan can continue
         │
         ├── Non-critical task → Skip, continue with remaining tasks
         │
         └── Critical task → Fail the entire workflow
```

### Consensus Flow

```
Multiple agents produce conflicting results
    │
    ▼
ConsensusEngine.resolve(topic, votes)
    │
    ├── 1. Weighted voting by confidence
    ├── 2. Evidence collection
    ├── 3. Reviewer override (optional)
    └── 4. Return ConsensusResult with decision
```

## Lifecycle

```
SwarmOrchestrator.start()
    │
    ├── Initialize all subsystems
    ├── Register agent types (13 built-in)
    ├── Start message bus
    └── Emit SWARM_STARTED

SwarmOrchestrator.run_workflow(goal)
    │
    ├── Plan decomposition (SwarmPlanner)
    ├── Task allocation (TaskAllocator)
    ├── Parallel execution (Coordinator → Dispatcher → Worker)
    ├── Result merging (ResultMerger)
    └── Return merged result

SwarmOrchestrator.stop()
    │
    ├── Cancel active workflows
    ├── Release conflict locks
    ├── Shut down subsystems
    └── Emit SWARM_STOPPED
```

## Extension Guide

### Adding a New Agent Type (Plugin)

```python
from swarm.registry import AgentTypeProfile
from swarm import SwarmOrchestrator

def register_my_agent(swarm: SwarmOrchestrator):
    profile = AgentTypeProfile(
        name="my-specialized-agent",
        description="Handles specialized task X",
        capabilities={"analysis", "custom_x"},
        cost_per_call=15,
        speed_rating=4,
        supported_tools=["terminal", "file", "web_search"],
    )
    swarm.register_agent_type(profile)
```

### Registering a Custom Decomposition Strategy

```python
def my_strategy(goal: str, context: dict) -> list[AgentTask]:
    if "database" in goal.lower():
        return [
            AgentTask(
                description="Design database schema",
                goal=f"Design a database schema for: {goal}",
                required_capabilities={"planning", "analysis"},
            ),
            AgentTask(
                description="Implement database layer",
                goal=f"Implement the database layer for: {goal}",
                required_capabilities={"coding"},
            ),
        ]
    return None  # Cannot handle this goal

swarm.planner.register_strategy(my_strategy)
```

### Using the Execution Monitor

```python
def on_progress(event_type: str, agent: AgentProgress):
    print(f"[{event_type}] {agent.description}: {agent.status}")

swarm.monitor.subscribe(on_progress)
```

## Design Principles

1. **No tight coupling** — All subsystems communicate through the EventBus / InterAgentMessageBus
2. **Single responsibility** — Each module has one job
3. **Backward compatibility** — Existing single-agent mode works unchanged
4. **Plugin-friendly** — New agent types can be registered at runtime
5. **Dependency injection** — Services receive dependencies through constructors
6. **Type hints throughout** — All public APIs are fully typed
7. **Fail-open** — Non-critical tasks can fail without blocking the workflow
8. **Observable by default** — All subsystems emit structured progress events

## Comparison: Single-Agent vs Multi-Agent

| Aspect | Single-Agent (Existing) | Multi-Agent (Swarm) |
|--------|------------------------|---------------------|
| Agent count | 1 | Many (specialized) |
| Task handling | Sequential reasoning | Parallel execution |
| Specialization | Generalist | Specialized per task |
| Complexity | Simple | Higher (orchestration) |
| Best for | Simple questions, quick tasks | Complex multi-step goals |
| Cost | Lower | Higher (multiple agents) |
| Enable | Default (always available) | Optional (swarm.start()) |
