# AetherOS Kernel Test Plan

Suites (run via `scripts/run_tests.sh` where available, else
`python -m pytest <path> -q -o addopts=""` on Windows):

- `tests/kernel/test_kernel_modules.py` — legacy kernel unit/integration
  (event bus, lifecycle, registry, planner, scheduler, executor, router,
  workspace, context, permissions, task graph, telemetry, state).
- `tests/kernel/test_agent_kernel.py` (new) — AgentKernel 1.0: boot,
  intent admission, agent lifecycle, syscall invocation, delegation subset,
  checkpoint/recovery, scheduler/resources, memory scoping, emergency stop.
- `tests/kernel/test_agent_kernel_security.py` (new) — §94 security
  invariants (10 executable tests) + injection/exfiltration/SSRF,
  expired approvals, revoked identity, emergency-stop override, simulation
  labeling.
- Existing repo suite must stay green for touched areas
  (`tests/aetheros_cli/`, `tests/agent/` smoke).

Evidence rules (§115–§117): never fabricate passes; mark
`BLOCKED / NOT RUN / REQUIRES_EXTERNAL_ENVIRONMENT / REQUIRES_HARDWARE /
REQUIRES_CREDENTIAL`; label `SIMULATION / REPLAY / MOCK /
HARDWARE_UNAVAILABLE / LIVE_HARDWARE`; no cross-platform claims without
execution on that platform.
