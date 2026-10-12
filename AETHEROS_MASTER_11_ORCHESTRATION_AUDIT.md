# AETHEROS MASTER 11 — ORCHESTRATION AUDIT

> **Phase 0**: Complete orchestration audit — identify all existing capabilities before implementing changes.
> **Non-negotiable**: Do not modify code until audit is complete.

---

## 1. CURRENT ORCHESTRATION ARCHITECTURE

### 1.1 Core Agent (run_agent.py)
**File**: `run_agent.py` (5369 lines) — Primary agent implementation

**AIAgent Class** (321-5110):
- Main agent with tool calling capabilities
- Supports multiple model providers (OpenAI, Anthropic, Codex, etc.)
- 200+ constructor parameters for configuration
- Delegates initialization to `agent.agent_init.init_agent()`
- Core methods: `run_conversation()`, `chat()`, `_run_codex_app_server_turn()`
- Built-in subagent delegation via `delegate_task` tool

**Key Components**:
- Tool system integration via `model_tools.py`
- Terminal, browser, file, vision, transcription, TTS tools
- Session management with SQLite (FTS5)
- Context compression & prompt caching
- Checkpoint system for long conversations
- Iteration budget tracking
- Credential pooling for rate limit handling

### 1.2 Orchestrator Layer (aetheros_orchestrator/)
**File**: `aetheros_orchestrator/orchestrator.py` (206 lines) — System-level orchestrator

**AetherosOrchestrator Class**:
- Manages subsystem lifecycle (logging, config, bus, api, mcp, reasoning, skills, platform, knowledge, ui, desktop)
- Dependency graph resolution for startup order
- Health checking with periodic checks
- Event bus (asyncio-based) + RPC server/client
- REST + WebSocket API servers
- Subsystem registration with startup/shutdown hooks

### 1.3 Automation Orchestration (aetheros_automation/orchestrator/)
**File**: `aetheros_automation/orchestrator/orchestrator.py` (915 lines) — Task orchestration engine

**TaskOrchestrator Class**:
- Plan management (`_plans`, `_execution_states`, `_agent_assignments`)
- NLP-based task decomposition (`_decompose_into_subtasks`)
- Role inference from goal text (`_infer_role`)
- Tool inference from task description (`_infer_tools`)
- Approval requirement detection (`_check_approval_required`)
- Execution graph building (`_build_execution_graph`)
- Plan validation & versioning
- Model routing integration (`ModelRouter`)
- Checkpoint management (`CheckpointManager`)
- Retry handling (`RetryHandler`)
- Result validation (`ResultValidator`)
- NLP automation engine for natural language understanding

### 1.4 Multi-Agent Integration (agent/multi_agent_integration/)
**File**: `agent/multi_agent_integration/coordination.py` (387 lines)

**MultiAgentCoordinator Class**:
- Collaboration session management (start/end sessions)
- Inter-agent messaging (send, broadcast, share results)
- Sub-agent creation and task execution
- Context sharing between agents

### 1.5 Automation Agents (aetheros_automation/agents/)
**Registry**: `aetheros_automation/agents/registry.py`

**Agent Registry** (`AgentRegistry`):
- Static registry mapping `AgentRole` → agent class
- Built-in agents: Coordinator, Developer, Browser, Research, Writer, QA, Deployment, Security, Memory, Planner, Creative, Data, Communication, Review, Coding, File
- Execution via `AgentRegistry.execute(role, task, context)`

**Agent Roles** (16 roles in `AgentRole` enum):
- COORDINATOR, DEVELOPER, BROWSER, RESEARCH, WRITER, QA, DEPLOYMENT, SECURITY, MEMORY, PLANNER, CREATIVE, DATA, COMMUNICATION, REVIEW, CODING, FILE

**Individual Agents** (15 agents in `aetheros_automation/agents/`):
- coordinator.py, developer.py, browser_agent.py, research.py, writer.py, qa.py, deployment.py, security.py, memory.py, planner_agent.py, creative.py, data_agent.py, communication_agent.py, review_agent.py, file_agent.py

### 1.6 Subagent Delegation (tools/delegate_tool.py)
**File**: `tools/delegate_tool.py` (2921 lines) — Subagent delegation system

**Key Features**:
- Spawns child AIAgent instances with isolated context
- Restricted toolsets (blocked: delegate_task, clarify, memory, send_message, execute_code)
- Role-based: `leaf` (default) vs `orchestrator` (can spawn subagents)
- Configurable depth limit (`max_spawn_depth`, default 1)
- Concurrent children limit (`max_concurrent_children`, default 3)
- Heartbeat monitoring with stale detection
- Progress callbacks for TUI/gateway relay
- Credential pooling for rate limit handling
- MCP toolset inheritance
- File-state coordination between parent/child
- Timeout management (default 600s per child)
- Approval callbacks (auto-deny by default)
- Pause/resume control
- Active subagent registry for TUI observability

### 1.7 Skills System
**Location**: `skills/` (20+ categories, 100+ skills)
- Categories: autonomous-ai-agents, creative, data-science, devops, email, github, media, mlops, note-taking, productivity, research, smart-home, social-media, software-development, etc.
- Skill format: `SKILL.md` frontmatter + procedures/scripts
- Skill commands injected as user messages (preserves prompt caching)
- `aetheros skills` CLI for management

### 1.8 Workflows System
**Location**: `workflows/`

**Components**:
- Engine (`engine.py`), Executor (`executor.py`), Scheduler (`scheduler.py`)
- Node system: actions, agent_nodes, ai, logic, mcp_nodes, triggers
- Marketplace, Store, Templates, Web interface
- Node-based workflow graph execution

### 1.9 Tools System
**Location**: `tools/` (80+ tools)

**Key Tools**:
- Vision: `vision_tools.py` (vision_analyze, video_analyze, screen_capture, image_ocr, screen_understand, document_extract)
- Transcription: `transcription_tools.py` (6 providers: local, groq, openai, mistral, xai, elevenlabs)
- TTS: `tts_tool.py` (10 providers: edge, elevenlabs, openai, minimax, mistral, gemini, xai, neutts, kittentts, piper)
- Delegate: `delegate_tool.py` (subagent spawning)
- Terminal: `terminal_tool.py` (local, docker, ssh, modal, daytona, singularity)
- Browser: `browser_tool.py` (playwright-based)
- File: `read_file`, `write_file`, `patch`, `search_files`
- Web: `web_search`, `web_extract`
- Memory: `memory_tool.py`
- Cron: `cronjob` tool

---

## 2. EXISTING AGENTS

| Agent | Type | Location | Capabilities |
|-------|------|----------|--------------|
| **Core AIAgent** | General | `run_agent.py` | Full tool access, conversation loop, multimodal, subagent delegation |
| **Coordinator** | Orchestration | `aetheros_automation/agents/coordinator.py` | Task decomposition, planning, delegation |
| **Developer** | Coding | `aetheros_automation/agents/developer.py` | Code generation, refactoring, debugging |
| **Browser** | Web | `aetheros_automation/agents/browser_agent.py` | Navigation, scraping, extraction |
| **Research** | Research | `aetheros_automation/agents/research.py` | Search, synthesis, citation |
| **Writer** | Content | `aetheros_automation/agents/writer.py` | Composition, editing, formatting |
| **QA** | Testing | `aetheros_automation/agents/qa.py` | Test generation, validation |
| **Deployment** | DevOps | `aetheros_automation/agents/deployment.py` | CI/CD, infrastructure |
| **Security** | Security | `aetheros_automation/agents/security.py` | Auditing, compliance |
| **Memory** | Knowledge | `aetheros_automation/agents/memory.py` | Storage, retrieval |
| **Planner** | Planning | `aetheros_automation/agents/planner_agent.py` | Task decomposition, scheduling |
| **Creative** | Creative | `aetheros_automation/agents/creative.py` | Design, generation |
| **Data** | Analytics | `aetheros_automation/agents/data_agent.py` | Analysis, visualization |
| **Communication** | Messaging | `aetheros_automation/agents/communication_agent.py` | Email, chat, notifications |
| **Review** | Review | `aetheros_automation/agents/review_agent.py` | Code review, proofreading |
| **Coding** | Coding | `aetheros_automation/agents/coding.py` | Specialized coding tasks |
| **File** | Files | `aetheros_automation/agents/file_agent.py` | File operations |

---

## 3. EXISTING AGENT INTERFACES

### 3.1 Core AIAgent Interface (`run_agent.py`)
```python
class AIAgent:
    def __init__(self,
        base_url: str = None,
        api_key: str = None,
        provider: str = None,
        api_mode: str = None,
        model: str = "",
        max_iterations: int = 90,
        enabled_toolsets: List[str] = None,
        disabled_toolsets: List[str] = None,
        save_trajectories: bool = False,
        verbose_logging: bool = False,
        quiet_mode: bool = False,
        tool_progress_mode: str = "all",
        ephemeral_system_prompt: str = None,
        # ... 170+ more parameters
    ):
        init_agent(self, ...)

    def run_conversation(self, user_message: str, system_message: str = None,
                         conversation_history: List[Dict] = None, task_id: str = None,
                         stream_callback: callable = None, persist_user_message: str = None) -> Dict:
        """Main entry point — returns final response + message history"""

    def chat(self, message: str, stream_callback: callable = None) -> str:
        """Simple interface — returns string response"""
```

### 3.2 BaseAgent Interface (`aetheros_automation/agents/registry.py`)
```python
class BaseAgent(ABC):
    @property
    @abstractmethod
    def role(self) -> AgentRole: ...

    @abstractmethod
    async def execute(self, task: Task, context: dict | None = None) -> str: ...
```

### 3.3 Delegate Tool Interface (`tools/delegate_tool.py`)
```python
def delegate_task(
    goal: str,
    context: str = None,
    toolsets: List[str] = None,
    model: str = None,
    max_iterations: int = None,
    role: str = "leaf",  # or "orchestrator"
    tasks: List[dict] = None  # for batch/parallel delegation
) -> str:
    """Spawns child agent(s) with isolated context"""
```

### 3.4 MultiAgentCoordinator Interface (`agent/multi_agent_integration/coordination.py`)
```python
class MultiAgentCoordinator:
    async def start_collaboration_session(agent_id, goal, participant_roles, context) -> str
    async def send_collaboration_message(collab_id, sender_id, content, message_type, data) -> Dict
    async def broadcast_to_collaboration(collab_id, sender_id, content, message_type) -> List
    async def share_collaboration_result(collab_id, agent_id, result_key, result_value)
    def get_collaboration_result(collab_id, result_key) -> Any
    async def create_sub_agent(parent_agent_id, role, goal, instructions, max_steps, max_time) -> Dict
    async def execute_sub_agent_task(sub_agent_id, task_goal, task_description, context) -> Dict
```

### 3.5 TaskOrchestrator Interface (`aetheros_automation/orchestrator/orchestrator.py`)
```python
class TaskOrchestrator:
    async def understand_objective(self, user_request: str) -> OrchestrationPlan
    async def analyze_task(self, plan: OrchestrationPlan) -> OrchestrationPlan
    async def create_execution_plan(self, plan: OrchestrationPlan) -> OrchestrationPlan
    async def execute_plan(self, plan_id: str, mode: GraphExecutionMode = GraphExecutionMode.SEQUENTIAL)
    async def execute_task(self, task: OrchestrationTask, agent: Any, context: dict) -> str
    def get_plan(self, plan_id: str) -> OrchestrationPlan
    def get_execution_state(self, plan_id: str) -> ExecutionState
    def create_checkpoint(self, plan_id: str) -> str
    async def restore_from_checkpoint(self, checkpoint_path: str)
```

---

## 4. EXISTING PLANNERS

### 4.1 NLPAutomationEngine (`aetheros_automation/nlp/nlp_automation.py`)
- Natural language → structured plan conversion
- Goal decomposition into subtasks
- Keyword-based role inference

### 4.2 TaskOrchestrator Planning (`aetheros_automation/orchestrator/planner.py`)
- Task decomposition into subtasks
- Role inference from keywords (`_infer_role`)
- Tool inference from keywords (`_infer_tools`)
- Approval requirement detection
- Execution graph building
- Cost/time estimation

### 4.3 TaskOrchestrator `_decompose_into_subtasks`
- Splits goal by sentences
- Assigns roles based on keywords (16 roles)
- Creates sequential dependency chain
- Estimates duration per task type

### 4.4 Core AIAgent Planning
- No explicit planner in core AIAgent
- Relies on model's reasoning + tool calling loop
- Delegation tool for manual subagent spawning

---

## 5. EXISTING TASK QUEUES

### 5.1 Cron System (`cron/`)
- `cron/jobs.py` — Job store (SQLite)
- `cron/scheduler.py` — Tick loop with file locking
- Supported schedules: duration, "every" phrases, cron expressions, ISO timestamps
- Per-job fields: skills, model/provider overrides, scripts, context chaining, multi-platform delivery
- 3-minute hard interrupt on cron sessions

### 5.2 Automation Orchestrator Task Queue
- Execution state tracking (`_execution_states`)
- Task status lifecycle: PENDING → QUEUED → RUNNING → COMPLETED/FAILED/CANCELLED
- Priority support (TaskPriority enum)
- Dependency-based ordering

### 5.3 Delegate Tool Thread Pool
- `ThreadPoolExecutor` with configurable `max_concurrent_children` (default 3)
- Per-child timeout (default 600s)
- Heartbeat monitoring with stale detection
- Active subagent registry

### 5.4 Cron Background Jobs
- `kanban.dispatcher` — Long-running dispatcher loop
- Kanban worker spawning
- Separate from main task queue

---

## 6. EXISTING WORKFLOWS

### 6.1 Workflows System (`workflows/`)
- Node-based graph execution (actions, AI, logic, triggers)
- Scheduler for recurring workflows
- Marketplace for sharing
- Web interface
- Node types: actions, AI, logic, MCP, triggers, agent_nodes

### 6.2 Kanban (Multi-Agent Work Queue)
- SQLite-backed board (`kanban/jobs.py`)
- Dispatcher loop (default 60s)
- Worker spawning with dedicated toolset
- Stale claim reclamation
- Failure limit auto-blocking (default 2)
- Plugin assets: dashboard, systemd service

### 6.3 Kanban Toolset (`tools/kanban_tools.py`)
- Worker tools: `kanban_show`, `kanban_complete`, `kanban_block`, `kanban_heartbeat`, `kanban_comment`, `kanban_create`, `kanban_link`
- Router tools: `kanban_list`, `kanban_unblock`

### 6.4 Delegate Tool Workflows
- Single task delegation
- Batch (parallel) delegation
- Role-based: `leaf` vs `orchestrator`
- Depth limiting (`max_spawn_depth`)
- Progress callbacks with TUI/gateway relay

---

## 7. EXISTING ROUTERS

### 7.1 Model Router (`aetheros_automation/routing/model_router.py`)
- Task-based model selection
- Cost/latency/quality optimization
- Provider fallbacks
- Role-based preferences (`_MODEL_ROLE_PREFERENCES`)

### 7.2 Capability Detector (`agent/multimodal/capability_detector.py`)
- Per-model modality detection (vision, audio, video, document, OCR, tools)
- Catalog + override + heuristics
- Modality → capability mapping

### 7.3 Input Router (`agent/multimodal/input_router.py`)
- File, URL, base64, text, structured, device, stream → MediaObject
- SSRF protection
- MIME type detection

### 7.4 Enhanced Routing (`agent/multimodal/enhanced_routing.py`)
- Complex routing decisions
- Multi-modal aware

### 7.5 Tool Router (`agent/multimodal/workflows.py`)
- `MultimodalToolRouter` — routes media to tools based on modality
- Category-based routing (VISION, OCR, STT, TTS, DOCUMENT, VIDEO, SCREEN, CAMERA, MEMORY, SEARCH, ANALYSIS)
- Confidence scoring based on task keywords

### 7.6 Capability-Based Agent Routing
- `AgentRegistry` — role-based static mapping
- `TaskOrchestrator._infer_role` — keyword-based role inference
- Delegate tool — explicit agent selection via `role` parameter

---

## 8. EXISTING SUBAGENT SUPPORT

### 8.1 Delegate Tool (`tools/delegate_tool.py`)
- Child agent spawning with isolated context
- Restricted toolsets (blocked tools)
- Role system: `leaf` vs `orchestrator`
- Depth limit (`max_spawn_depth`)
- Concurrency control (`max_concurrent_children`)
- Batch (parallel) and single modes
- Progress callbacks with identity tracking
- Credential pooling
- Timeout management
- Approval callbacks
- Pause/resume
- Active subagent registry

### 8.2 Automation Sub-Agent Manager (`aetheros_automation/multi_agent/sub_agent_manager.py`)
- Sub-agent creation with role, goal, instructions
- Task execution with context
- Agent lifecycle management

### 8.3 MultiAgentCoordinator (`agent/multi_agent_integration/coordination.py`)
- Collaboration sessions
- Inter-agent messaging
- Sub-agent creation
- Task execution with context sharing

### 8.4 Core AIAgent Subagent Integration
- `_delegate_depth` tracking
- `_subagent_id` identity
- Active children registry
- Credential pool sharing
- Interrupt propagation
- Plugin hooks (`subagent_start`)

---

## 9. EXISTING RETRY SYSTEMS

### 9.1 RetryHandler (`aetheros_automation/recovery/retry.py`)
- Exponential backoff with jitter
- Configurable max attempts
- Retryable failure classification

### 9.2 FallbackHandler (`aetheros_automation/recovery/fallback.py`)
- Fallback chain execution
- Provider/model fallbacks

### 9.3 Delegate Tool Retry
- Per-child timeout (default 600s)
- Heartbeat monitoring with stale detection
- Stale detection thresholds (idle vs in-tool)
- ThreadPoolExecutor with timeout

### 9.4 Core Agent Retry
- `jittered_backoff` utility
- `IterationBudget` tracking
- `handle_max_iterations` handler

---

## 10. EXISTING VERIFICATION

### 10.1 ResultValidator (`aetheros_automation/validation/validator.py`)
- Task result validation
- Schema validation
- Custom validators

### 10.2 Delegate Tool Verification
- Child agent result structure validation
- Output tail extraction for TUI
- Error output detection (`_looks_like_error_output`)

### 10.3 Core Agent Verification
- `ContextCompressor` — context compression with verification
- `sanitize_context` — message sanitization
- Tool result classification (`tool_result_classification.py`)

### 10.4 ResultValidator (`aetheros_automation/validation/validator.py`)
- Schema validation
- Custom validators
- Evidence requirements per task type

---

## 11. EXISTING APPROVAL SYSTEMS

### 11.1 Approval System (`tools/approval.py`, `tools/terminal_tool.py`)
- `prompt_dangerous_approval()` — interactive approval prompt
- Approval modes: once, session, always, deny, deny_session
- Per-session approval queue (gateway)
- Auto-deny/auto-approve callbacks for subagents

### 11.2 Delegate Tool Approval
- Configurable: `delegation.subagent_auto_approve` (default false → auto-deny)
- `_subagent_auto_deny` / `_subagent_auto_approve` callbacks
- Installed in subagent worker threads

### 11.3 Approval Models (`aetheros_automation/models/models.py`)
- `ApprovalRequest` — pending approval with details
- `ApprovalAction` enum (12 action types)
- `ApprovalResponse` enum (5 response types)

### 11.4 TaskOrchestrator Approval
- `requires_approval` flag on tasks
- `approval_actions` list (12 action types)
- `approval_response` tracking
- `ApprovalAction` enum (12 types)

---

## 12. EXISTING STATE MANAGEMENT

### 12.1 SessionDB (`aetheros_state.py`)
- SQLite with FTS5
- Session CRUD + message history
- Parent/child session linking
- Forking/branching support

### 12.2 Automation Orchestrator State
- `_plans`, `_execution_states`, `_agent_assignments`
- `_sub_agents`, `_agent_messages`, `_active_agents`
- Lifecycle registry (`LifecycleRegistry`)
- Checkpoint manager

### 12.3 Delegate Tool State
- Module-level: `_spawn_paused`, `_active_subagents`
- Per-child: heartbeat tracking, stale detection
- Thread-local approval callbacks
- File-state coordination (`file_state` module)

### 12.4 SessionDB
- SQLite + FTS5
- Session hierarchy (parent/child)
- Fork/branch support
- Message history with tool calls

### 12.5 Checkpoint System
- `CheckpointManager` — plan/task checkpoints
- `ContextCompressor` — context compression checkpoints
- Delegate tool file-state coordination

---

## 13. EXISTING PROBLEMS

### 13.1 Fragmented Orchestration Layers
- **3 separate orchestration systems**:
  1. `aetheros_orchestrator` — subsystem lifecycle
  2. `aetheros_automation/orchestrator` — task orchestration
  2. `agent/multi_agent_integration` — multi-agent coordination
  4. `run_agent.py` delegate tool — subagent spawning
  5. `workflows/` — node-based workflows
  6. `cron/` — scheduled jobs
  7. `kanban/` — multi-agent work queue
- No unified orchestration API
- Different task models, state stores, APIs

### 13.2 Inconsistent Agent Interfaces
- Core `AIAgent` — 200+ params, tool-heavy, synchronous
- `BaseAgent` (automation) — async `execute(task, context)`
- `AIAgent` subagents — constructor-injected, restricted toolsets
- Automation agents — `BaseAgent` subclasses with `execute(task, context)`
- No common interface for all agent types

### 13.3 No Unified Task Model
- Core: implicit in conversation + `task_id` string
- Automation: `OrchestrationTask` + `Task` + `TaskStep`
- Delegate: implicit in `goal` + `context`
- Kanban: `KanbanJob` with assignees/claims
- Cron: `CronJob` with schedule/context
- Workflows: `Workflow` + `Task` + `TaskStep`

### 13.4 No Unified Agent Registry
- `AgentRegistry` (automation) — static role→class mapping
- Core: implicit via toolsets + model selection
- Delegate: implicit via role + toolsets
- No discovery, health checks, capability queries

### 13.5 No Capability-Based Routing
- Role-based routing only (`AgentRegistry`)
- Toolset-based routing (`MultimodalToolRouter`)
- No capability queries (what can this agent actually do?)
- No health-aware routing

### 13.6 No Unified Planning
- Core: model reasoning + tool loop
- Automation: `NLPAutomationEngine` + `TaskOrchestrator._decompose_into_subtasks`
- Delegate: manual via `delegate_task` tool
- Workflows: node graph definition
- No adaptive replanning on failure/change

### 13.7 No Unified Context Isolation
- Core: `_delegate_depth`, `_subagent_id`, file-state coordination
- Automation: separate `Task` contexts
- Delegate: isolated conversation, restricted toolsets
- No cross-system context isolation guarantees

### 13.8 Duplicate Subagent Systems
- Delegate tool (`delegate_tool.py`)
- Automation `SubAgentManager`
- `MultiAgentCoordinator.create_sub_agent`
- Kanban workers (separate agent spawning)

### 13.9 No Unified Health/Observability
- Orchestrator health checks (subsystems)
- Delegate tool active subagent registry
- No agent health API
- No capability health checks

---

## 14. DUPLICATE SYSTEMS

| Functionality | Implementations |
|---------------|-----------------|
| **Task/Job Queue** | Cron scheduler, Kanban dispatcher, Delegate ThreadPool, Automation execution engine |
| **Agent Registry** | Automation AgentRegistry, Core implicit, Delegate implicit |
| **Subagent Spawning** | Delegate tool, SubAgentManager, MultiAgentCoordinator, Kanban worker spawn |
| **Task/Workflow Engine** | Workflows engine, Automation orchestrator, Cron scheduler, Kanban, Core conversation loop |
| **Agent Registry** | Automation AgentRegistry, Core implicit, Delegate implicit |
| **Context/State** | SessionDB, Automation state, Delegate module-level, File-state, Kanban board |
| **Planning** | NLP engine, Orchestrator decomposition, Manual delegate, Workflow node graph |
| **Approval** | Terminal approval, Subagent callbacks, Automation ApprovalRequest |
| **Context Isolation** | Delegate isolated convos, Automation Task contexts, Core session hierarchy |

---

## 15. MISSING ORCHESTRATION CAPABILITIES

### 15.1 Universal Agent Interface
- No common interface across all agent types
- No capability discovery
- No health checks
- No versioning

### 15.2 Unified Agent Registry
- No discovery API
- No capability queries
- No enable/disable
- No health checks

### 15.3 Capability-Based Routing
- Only role-based + toolset-based
- No capability discovery
- No performance-aware routing

### 15.4 Unified Task Object
- No common task schema
- No task graph with DAG semantics
- No standard lifecycle
- No standard result contract

### 15.5 Adaptive Planning
- No replanning on failure/change
- No plan versioning
- No dry-run support

### 15.6 Multi-Agent Coordination
- Limited handoff protocols
- No standard message types
- No context packaging standards
- No consensus/review modes

### 15.7 Verification System
- No independent verification agent
- No standard evidence requirements
- No success criteria definition

### 15.8 Resource Management
- No unified budget tracking
- No fair scheduling
- No concurrency limits per user/project

### 15.9 Unified Observability
- No structured event stream
- No live progress API
- No task/agent inspectors

---

## 16. FILES THAT NEED MODIFICATION

### Core Orchestration (New/Modified)
| File | Purpose |
|------|---------|
| `agent/orchestration/` | **NEW** — Unified orchestration layer |
| `agent/orchestration/agent_interface.py` | Universal agent interface |
| `agent/orchestration/agent_registry.py` | Unified agent registry |
| `agent/orchestration/task.py` | Universal task object + lifecycle |
| `agent/orchestration/task_graph.py` | DAG task graph |
| `agent/orchestration/planner.py` | Planning engine + adaptive replanning |
| `agent/orchestration/router.py` | Capability-based router |
| `agent/orchestration/health.py` | Agent health monitoring |
| `agent/orchestration/handoff.py` | Agent handoff protocols |
| `agent/orchestration/verification.py` | Verification agent + evidence |
| `agent/orchestration/queue.py` | Unified task queue |
| `agent/orchestration/observability.py` | Structured events + live progress |
| `agent/orchestration/approval.py` | Unified approval system |
| `agent/orchestration/budget.py` | Resource budgets + fair scheduling |
| `agent/orchestration/state.py` | Durable task state + checkpoints |
| `agent/orchestration/recovery.py` | Crash recovery + stall detection |
| `agent/orchestration/__init__.py` | Public API exports |

### Integration Points (Modified)
| File | Changes |
|------|---------|
| `run_agent.py` | Integrate with universal task system, use new planner |
| `tools/delegate_tool.py` | Use unified agent interface, handoff protocol |
| `aetheros_automation/orchestrator/orchestrator.py` | Migrate to unified task model |
| `aetheros_automation/orchestrator/planner.py` | Use universal planner |
| `aetheros_automation/orchestrator/routing.py` | Use capability router |
| `tools/delegate_tool.py` | Use universal agent interface + handoff |
| `aetheros_automation/orchestrator/execution_engine.py` | Use unified task model |
| `agent/multi_agent_integration/coordination.py` | Use unified handoff protocol |
| `tools/delegate_tool.py` | Use universal handoff protocol |
| `aetheros_automation/agents/registry.py` | Extend with capability/health |
| `aetheros_orchestrator/orchestrator.py` | Integrate with unified task queue |
| `aetheros_cli/commands.py` | Add orchestration CLI commands |
| `tools/approval.py` | Unify with new approval system |
| `aetheros_cli/cli_commands_mixin.py` | Add orchestration CLI |

---

## 17. FILES THAT MUST REMAIN UNCHANGED

| File | Reason |
|------|--------|
| `run_agent.py` | Core agent loop — prompt caching sacred |
| `cli.py` | CLI orchestrator — slash command registry stable |
| `model_tools.py` | Tool orchestration — core tool schema stable |
| `toolsets.py` | Toolset definitions — core tools stable |
| `aetheros_constants.py` | Profile-aware paths — critical for isolation |
| `aetheros_logging.py` | Logging setup — stable |
| `aetheros_state.py` | Session DB — stable schema |
| `tools/registry.py` | Tool registry — core registration stable |
| `aetheros_cli/config.py` | Config loader — stable API |
| `aetheros_cli/skin_engine.py` | Skin system — stable data format |
| `aetheros_cli/commands.py` | Slash command registry — stable |
| `gateway/run.py` | Gateway runner — stable message flow |
| `agent/conversation_loop.py` | Conversation loop — prompt caching critical |
| `agent/prompt_caching.py` | Prompt caching — must not break |
| `agent/conversation_compression.py` | Context compression — only cache-break allowed |
| `agent/skill_commands.py` | Skill slash commands — cache-aware pattern |
| `tools/computer_use/` | Computer use tools — MASTER 3 integration |
| `aetheros_orchestrator/orchestrator.py` | Subsystem lifecycle — stable |
| `aetheros_automation/orchestrator/orchestrator.py` | Core orchestration — stable core |
| `tools/delegate_tool.py` | Subagent delegation — stable core logic |

---

## 18. INTEGRATION WITH MASTER 1-10

| Master | Integration Point |
|--------|-------------------|
| **MASTER 1** (Core Brain) | `run_agent.py` conversation loop → unified task system |
| **MASTER 2** (Coding Agent) | Developer agent + screen_understand for visual coding |
| **MASTER 3** (Browser/Computer) | Browser agent + screen_capture + computer-use vision |
| **MASTER 4** (Research) | Research agent + multimodal context builder |
| **MASTER 5** (Agent Systems) | Agent registry + handoff protocols |
| **MASTER 6** (Model Routing) | Capability router + model selection per subtask |
| **MASTER 7** (Security) | Approval system + permissions + sandbox |
| **MASTER 8** (Skills/Plugins) | Skill-aware planning + tool selection |
| **MASTER 9** (Memory) | Memory-aware planning + artifact provenance |
| **MASTER 10** (Multimodal) | Multimodal-aware planning + context builder |

---

## 19. NEXT STEPS

1. **Phase 0**: Complete this audit ✅
2. **Phase 1**: Create universal agent interface (`agent/orchestration/agent_interface.py`)
3. **Phase 2**: Build unified agent registry (`agent/orchestration/agent_registry.py`)
3. **Phase 3**: Implement capability-based router (`agent/orchestration/router.py`)
4. **Phase 4-5**: Agent health checks
4. **Phase 6-7**: Universal task object + lifecycle
5. **Phase 8-9**: Task graph + decomposition
6. **Phase 10-13**: Planning engine + validation + versioning + adaptive
6. **Phase 14-17**: Agent/model/skill/tool selection
7. **Phase 18-19**: Memory-aware + multimodal-aware planning
7. **Phase 20-24**: Execution modes (single, multi, parallel, sequential, hybrid)
8. **Phase 25-29**: Handoff + context packaging + isolation + communication
8. **Phase 30-35**: Result contracts + verification + evidence
9. **Phase 36-43**: Failure handling + retry + fallback + checkpoints + cancellation
9. **Phase 44-50**: Deadlines + budgets + rate limiting + concurrency + recursion + loops
10. **Phase 51-55**: Approval gates + dry-run + preview
10. **Phase 56-60**: Safe execution + transactions + artifacts + provenance
11. **Phase 61-67**: Observability + UI + inspectors
11. **Phase 68-74**: Collaboration patterns + specialist routing + project/user awareness
12. **Phase 75-84**: Domain orchestration + long-running + heartbeats + stalls + background + notifications
12. **Phase 85-95**: Priority + queue + durability + recovery + idempotency + security
13. **Phase 96-100**: Tests + security + performance + regression + final report

---

## 20. TEST STRATEGY

### Test Files Needed
- `tests/orchestration/test_agent_interface.py`
- `tests/orchestration/test_agent_registry.py`
- `tests/orchestration/test_task_lifecycle.py`
- `tests/orchestration/test_planner.py`
- `tests/orchestration/test_router.py`
- `tests/orchestration/test_handoff.py`
- `tests/orchestration/test_verification.py`
- `tests/orchestration/test_recovery.py`
- `tests/orchestration/test_observability.py`
- `tests/orchestration/test_integration.py` (full regression)

### Integration Tests
- Single agent execution
- Multi-agent parallel/sequential/hybrid
- Agent handoff with context preservation
- Retry/fallback/cancellation
- Checkpoint/resume
- Approval gates
- Resource budgets
- Recursion limits

---

*Generated by Phase 0 audit. Do not modify code until audit review is complete.*