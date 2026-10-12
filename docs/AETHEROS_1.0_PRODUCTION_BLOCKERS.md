# AetherOS 1.0 Production Blockers (Master 75 §195)

No hidden blockers. Each: what / why / required infrastructure / impact / next action.

## P0-1 — No production signing credentials
What: Windows EV cert, Apple Developer ID, Play signing, TestFlight access all absent.
Why: never provisioned in this environment. Required infra: certs + funded
developer accounts + macOS runner. Impact: no artifact can be SIGNED; stable
release impossible. Next: provision via release engineering; until then every
signing step fails closed (proven).

## P0-2 — No packaged production artifacts
What: zero installers exist for 1.0.0. Why: (a) pre-existing design-system
typecheck errors break `tsc -b`; (b) P0-1. Required infra: fixed tree + build
runners. Impact: nothing to verify, deploy, or install. Next: fix B74-004,
run update-release.yml.

## P0-3 — No on-device validation evidence
What: install/launch/auth/update/rollback never executed on hardware or VMs.
Required infra: device lab (Windows/mac/Linux machines, ARM hardware, mobile
devices) + signed builds. Impact: platform matrices are logic-only. Next:
Master 74 exit criteria carried forward.

## P1-1 — Python CLI updater tests failing (22)
What: tests/aetheros_cli/test_cmd_update.py (18) + test_update_autostash.py (4)
fail with `TypeError: sequence item 0: expected str instance, MagicMock found`
at aetheros_cli/main.py:8178. Required: owner in CLI team to fix join/mock
mismatch. Impact: CLI self-update path untrusted. Next: fix + regression.

## P1-2 — Full python suite not completed here
What: 36,234 tests collected; wrapper full run exceeded the 10-minute
execution budget; raw pytest shows 24 pre-existing collection errors
(import collisions inanes like tests/security/test_runtime.py collecting fine
alone). Required: CI with xdist + isolation (run_tests.sh) and time.
Impact: production certification cannot cite full-suite green. Next: CI run.

## P1-3 — No production operations
What: no monitoring, alerting, incident drill, backup/restore drill, or fleet
telemetry deployment. Required: staging/prod infra. Impact: cannot operate
1.0. Next: stand up per runbook before any GO.
