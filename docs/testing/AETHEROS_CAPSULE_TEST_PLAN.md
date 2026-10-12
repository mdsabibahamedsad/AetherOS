# AetherOS Capsule Test Plan

## Suites (hermetic: stub runtime, bus off, tmp capsule roots, no net/creds/hw)

- `tests/kernel/test_agent_capsule.py` (26 tests): full lifecycle,
  invalid transitions, admission validation, parent subset + depth,
  14 profiles, unknown-profile rejection, untrusted restrictiveness,
  isolation detection honesty, no-above-detected-level, FS write/read +
  read-only + COW, offline/allowlist network denial, secret mediation +
  scoping + provider-only plaintext + revocation, risk determinism,
  quarantine→forensic→release cycle, snapshot/restore/migration
  (+ remote REQUIRES_CONFIGURATION), tampered-snapshot rejection,
  replay defaults, revocation, simulate purity, diff/preview,
  child quota, swarm quota, GC + leak scan, SDK `capsules.*`.
- `tests/kernel/test_agent_capsule_security.py` (55 tests): 11 × §111
  invariants, 16 path-escape + 13 SSRF probes, live symlink rejection,
  env-leak block, 5 injection payloads + tool-input screening,
  4 × §114 malicious-agent, 4 × §115 chaos.

Run per-file (repo convention): `scripts/run_tests.sh
tests/kernel/test_agent_capsule.py` or
`<venv>/Scripts/python.exe -m pytest tests/kernel/test_agent_capsule*.py`.

## Long-running (§116) — procedure, not yet executed

Run a capsule pool for an extended period sampling `capsule_resources`,
`leak_scan`, FS `metadata()`, receipt/egress log lengths, and CPU every
minute; assert bounded growth after `gc()`. Status: NOT_TESTED here.

## Chaos (§115) — executed subset

Exhaustion containment, policy-update re-evaluation (incl.
expiry→TERMINATE), credential-expiry denial, crash→snapshot recovery:
all PASS. Not executed: network loss, node crash, disk/memory/GPU
pressure, browser/device disconnect (REQUIRES_HARDWARE/ENVIRONMENT).

## Conventions (§125)

Results use IMPLEMENTED / TESTED / PARTIALLY_TESTED / NOT_TESTED /
UNAVAILABLE / BLOCKED. No benchmark, isolation, escape, hardware, VM,
container, migration, or certification result is claimed without the
executing test named above.
