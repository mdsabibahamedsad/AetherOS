# AetherOS Agent Kernel 1.0 — Implementation Report

## What was built (on top of existing `kernel/core/`)

The repo already contained a substantial `kernel/core/` (25 subsystems,
`AgentKernel`, canonical `types.py`). This change completes Master 57 by
fixing integration bugs and adding the missing control-plane surface —
no second desktop, no duplicate scheduler/memory/router/policy systems:

**Fixes (real bugs, reproduced first):**
- `kernel/core/kernel.py` — `create_agent_process()` treated
  `AdmissionResult` as a dict (`TypeError`); double authority grant;
  `start_agent()` drove `CREATED→ADMITTED→READY` while
  `AgentProcessManager` expected `INITIALIZING→READY`; shutdown joined
  daemon loops with 5s timeouts (slow shutdown). Fixed: object access,
  admission-grant reuse, `CREATED→ADMITTED→INITIALIZING→READY`, 0.2s joins.
- `kernel/core/types.py` — allowed `ADMITTED→READY/INITIALIZING`,
  `PAUSED→READY`, `READY→CHECKPOINTING`, `WAITING/BLOCKED→READY` so the
  scheduler, pause/resume, and init paths agree.
- `kernel/core/scheduler.py` — `admit()` forced `CREATED→READY` (invalid);
  now `CREATED→ADMITTED`.
- `kernel/core/agent_process_manager.py` — `_create_agent_instance()`
  constructed a live `AIAgent` during admission (hung without credentials);
  now an isolated stub by default (`AETHEROS_KERNEL_REAL_AGENT=1` opts into
  live). Tolerant `READY` transitions.
- `kernel/core/capability_invoker.py` — treated `PolicyEvaluationResult` /
  `SecurityCheckResult` as dicts (`.get` → `AttributeError` path); missing
  `DataClassification` import (`NameError`). Fixed with object-aware
  interpreters.
- `kernel/core/checkpoint_manager.py` — `create_checkpoint()` passed
  non-existent `checkpoint_type`/`tags` kwargs to `Checkpoint`; now stored
  in `metadata`.
- `kernel/core/tool_manager.py` — `discover_tools()` passed `[]` (selects
  nothing) and read `tool_def["name"]` on OpenAI-format defs (always
  `None`); now `None` + `function.name`. Discovery: 0 → 72 tools.
- `kernel/core/authority_manager.py` — `revoke_grant()` set
  `expires_at=now`, still valid under `now > expires_at`; now `now-1`
  (fail-closed; caught by new security test).
- Pre-existing repo breakage (blocked all CLI verification):
  `agent/memory_os/retrieval.py:36` and `benchmark/reports.py:109`
  multiline f-strings (`SyntaxError`); fixed minimally. Full-`main.py`
  CLI still has a pre-existing top-level `agent` subparser conflict
  (`agents/cli.py` vs built-in) — untouched, out of scope; kernel CLI
  verified standalone.

**New (Master 57 surface):**
- `kernel/core/syscalls.py` — canonical syscall catalog (§8): 27 aliases
  (`fs.*`, `terminal.execute`, `browser.*`, `computer.*`, `memory.*`,
  `research.*`, `automation.*`, `agent.spawn/delegate`, …) over existing
  tools + 5 kernel-native (`agent.spawn/delegate`, `memory.read/write`,
  `checkpoint.create`) + 4 fail-closed `REQUIRES_HARDWARE` stubs.
- `kernel/core/sdk.py` — `KernelSDK` (§106), authority-enforcing.
- `AgentKernel.emergency_stop/emergency_resume/is_stopped` (§31–§32).
- `kernel/benchmark.py` (§88), `kernel/doctor.py` (§114).
- `aetheros_cli/subcommands/kernel.py` + `main.py` wiring (§66):
  16 verbs (status/agents/agent/capabilities/resources/policies/trace/
  checkpoint/pause/resume/cancel/replay/stop/benchmark/security/nodes/doctor).
- Docs (§95): 14 files under `docs/architecture/`, `docs/benchmarks/`,
  `docs/testing/` (this report + 4 siblings under `docs/`).
- Tests: `tests/kernel/test_agent_kernel.py` (10),
  `tests/kernel/test_agent_kernel_security.py` (12, incl. §94 invariants).

## Integrations (§119)

Reused, not duplicated: `tools/registry.py` (72 tools as `tool.*` +
aliases), `cron/` via scheduler, memory providers via `MemoryManager`,
`providers/` via `ModelManager`, MCP/A2A through the
capability/authority pipeline (mediated, never bypass). Browser/computer
(syscalls over `browser_*`/`computer_use`/`screen_*` tools), research
(`web_search/extract`), automation (`automation_*`), swarm (scheduler
workload), economy/A2A (governed capabilities), evaluation hooks
(benchmark/doctor), world-model/cognitive/ambient/physical via
scope-gated capabilities + hardware BLOCKED stubs.
