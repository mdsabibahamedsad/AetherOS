# AetherOS Agent Kernel 1.0 — Test Report

Executed on Windows, Python 3.11.15, hermetic (stub agent runtime, no
network/credentials). Command: `python -m pytest <path> -q -o addopts=""`
(`scripts/run_tests.sh` is POSIX-only; `-o addopts=""` neutralizes the
repo's pytest-timeout addopts, which are not installed on this host).

## Results

- `tests/kernel/` (full dir): **202 passed, 0 failed** (~29s).
  - `tests/kernel/test_kernel_modules.py`: 119 passed (legacy suite, no
    regressions from transition/discovery/revoke changes).
  - `tests/kernel/test_agent_kernel.py`: 10 passed (boot, admission,
    lifecycle, syscalls, delegation, checkpoints, catalog, e-stop, memory
    scoping, SDK).
  - `tests/kernel/test_agent_kernel_security.py`: 12 passed (§94
    invariants + injection/SSRF).
  - Remainder: `test_multi_agent_orchestrator.py` et al.
- `aetheros kernel` CLI smoke (standalone argparse harness, since full
  `main.py` has a pre-existing `agent` subparser conflict): all verbs
  `status/capabilities/policies/resources/security/doctor/benchmark/nodes`
  return rc 0 with real kernel state.

## Not run / blocked

- Full repo suite (thousands of tests, needs POSIX wrapper + API keys):
  NOT RUN — scoped runs above are the evidence; no full-suite claim made.
- Live `AIAgent` execution, cloud models, hardware (robot/device),
  cross-platform (Linux/macOS): NOT RUN / REQUIRES_HARDWARE /
  REQUIRES_CREDENTIAL — stub runtime used; hardware syscalls return
  BLOCKED, never faked.
