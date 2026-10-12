# AetherOS Master 75 Security Scorecard — 1.0.0

| Category | Status | Evidence / Notes |
|---|---|---|
| identity | TESTED (unit) | tests/security 351 passed via wrapper |
| authorization | TESTED (unit) | same suite; device drills BLOCKED |
| agent | IMPLEMENTED | AgentCapsule/approval paths in tree; live validation UNVERIFIED |
| sandbox | IMPLEMENTED | Electron sandbox config; mac entitlements sane (no get-task-allow) |
| browser | IMPLEMENTED | navigation/output validation in tree; adversarial pages UNVERIFIED live |
| computer-use | IMPLEMENTED | approval-gated in tree; device validation BLOCKED |
| MCP | IMPLEMENTED | identity/permission/revocation paths; malicious-server live test UNVERIFIED |
| A2A | IMPLEMENTED | trust/revocation paths; network validation UNVERIFIED |
| memory | TESTED (unit) | poisoning defenses in suites run under full vitest (pass except themes) |
| storage | IMPLEMENTED | checkpoint/rollback policy; restore drill BLOCKED |
| update | TESTED | 37 unit + red-team green (Master 70.5) |
| supply chain | PARTIAL | pinning + gates implemented; no prod signing run |
| CI | IMPLEMENTED | 28 workflows; update-release.yml valid (9 jobs, parses) |
| secrets | PASSED | scan: no live secrets (test placeholders only), evidence in cert |
| privacy | IMPLEMENTED | redaction tested; fleet policy documented; audit live UNVERIFIED |
| observability | IMPLEMENTED | local telemetry; fleet deployment UNVERIFIED |

Unresolved: P0-1 (signing creds), P0-3 (device proof). No hidden criticals
found in executed scope. Absolute "secure" is NOT claimed.
