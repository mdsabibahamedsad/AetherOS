# Master 62 — Test Report (2026-09-09)

Env: Windows, Python 3.12.13, `TZ=UTC LANG=C.UTF-8 PYTHONHASHSEED=0`,
hermetic `AETHEROS_HOME` per test. (`scripts/run_tests.sh` wrapper is
broken on this Windows checkout — path mangling `D:\mnt\d\...` — so
pytest was invoked directly with the wrapper's env; same hermeticity.)

## Results

| Suite | Command | Result |
|---|---|---|
| Platform (contracts, e2e, security, fuzz, mcp/a2a, schemas, CLI, examples, signing) | `pytest tests/aetheros_platform/ -q -p no:cacheprovider` | **54 passed** (was 36 pass + 3 fail at baseline) |
| Plugin/extension SDK | `pytest tests/test_sdk.py` | **30 passed** |
| Combined | both above | **84 passed, 0 failed** (95s) |
| TypeScript SDK | `npm test` in `sdks/typescript` | **4 passed** offline; **4 passed** live vs gateway :8765 incl. extended E2E |
| Adjacent suites (`test_toolsets`, skills config) | pytest | 61 passed |
| Full 5-min workflow (`init`→key→serve→run→`test`) | manual, isolated HOME :8768 | PASS (`agent.py` COMPLETED, generated `test_agent.py` PASS) |
| All 8 shipped examples | `test_examples.py` + manual runs | PASS (executed, not just compiled) |
| Benchmarks | `python -m aetheros_platform.bench` | measured (see performance report) |

## Test matrix coverage (§102)

Schema ✓ API ✓ Gateway ✓ Auth ✓ Authz ✓ Policy ✓ SDK-TS ✓ SDK-Py ✓
CLI ✓ Agent ✓ Tool ✓ Skill ✓ Extension (sdk) ✓ MCP (real stdio) ✓ A2A
(real HTTP) ✓ Streaming (real SSE) ✓ Webhook (sign/verify/replay) ✓
Idempotency ✓ Rate-limit (trips real bucket) ✓ Quota (ledger, no fake
cost) ✓ Artifact ✓ Memory ✓ Automation ✓ Security (13 adversarial) ✓
Fuzz (870 cases) ✓ Replay: PARTIAL (event/audit trail exists, no
replay runner) ✓ Migration (SemVer/versioning unit) ✓ Compatibility
(matrix executed) ✓ Examples ✓ Docs (generated from code; hand docs
verified command-by-command except the published site build).

NOT covered here: browser/computer execution (no browser runner in this
env — SDK declares capabilities, enforcement unit-tested), macOS/Linux
runners, OAuth/OIDC flows (unimplemented), remote marketplace.

## Pre-existing failures (NOT caused by this phase, NOT fixed here)

- `tests/aetheros_knowledge/test_master14_new_features.py::TestKnowledgeCLI`
  (2 tests): imports `plt_handle_knowledge` from
  `aetheros_platform/cli.py`, which a prior phase's rewrite removed
  (present in HEAD, absent in worktree). Reproduced with my changes
  stashed. Out of scope: restoring Master-14 knowledge commands into
  the rewritten dev CLI.
- `python -m aetheros --help` crashes at startup (`conflicting
  subparser: agent`, `aetheros_cli/agent_network_cmd.py:34` vs
  `agents/cli.py:445`). Pre-existing; blocks main-binary `aetheros dev`
  integration (documented, not worked around).
