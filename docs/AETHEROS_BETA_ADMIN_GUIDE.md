# AetherOS Beta Admin Guide — 1.1.0-beta.1

## Cohorts and rollout

Target cohorts: CANARY_1 → CANARY_5 → BETA_10 → BETA_25 → BETA_50 → BETA_100
(policy targets, not usage claims). Cohorts may slice by device, platform,
organization, or account. Start at the channel maximum (`beta`: 10%) and
expand only on gate PASS:

```
node services/update/scripts/set-rollout.mjs --percentage 25
```

Gate logic (`apps/desktop/src/release/beta-gates.ts`, `evaluateRolloutGate`):
thresholds crash ≤2%, startup failure ≤1%, update failure ≤5%, auth failure
≤1%; any security alert or critical user report → ROLLBACK; any missing
telemetry → UNVERIFIED (do not expand on UNVERIFIED).

## Feature flags

Signed envelopes only (`signFlags`/`verifyFlags`). Clients check signature,
scope, and expiry. `SECURITY_LOCKED` flags (`disableSignatureVerification`,
`disableAuthentication`, `disableSandbox`, `disableAuditLog`,
`elevateAutonomy`) are rejected even when signed. Flags are auditable and
reversible; never a security bypass.

## Kill switch

- Pause/halt: `set-rollout.mjs --percentage 0` or `--kill`.
- Revoke: `revoke-release.mjs <release|artifact|channel|version>`.
- Clients treat kill-switched manifests as revoked and refuse install.
- Artifacts are never deleted by a pause (retention policy: current +
  previous + security fallback).

## Monitoring and incidents

Collect: install/launch/update/rollback outcomes, crash counts, startup
latency, agent task success, API errors, resource pressure. Severity SEV0–SEV3
(SEV0 = active compromise / severe data loss / critical release issue).
Workflow: detect → triage → contain → investigate → mitigate → recover →
communicate → postmortem. Resume rollout only after root cause + mitigation +
verification + approval.

## Rollback and promotion

Rollback types: application (reinstall previous-known-good), data (restore
from Master 61 checkpoint — never destructive-auto), schema (expand/contract),
configuration (re-apply pinned config). Promotion RC → Canary → 10 → 25 →
50 → 100 → Exit Review records requester, reviewer, commit, artifacts,
security/QA/performance status, and known issues.

## Telemetry fields (privacy)

Allowed: version, channel, platform, outcome, durationMs, artifactBytes,
failureReason (capped lengths). Forbidden: user content, prompts, memory,
files, secrets. Support bundles pass through `redactSecrets`/`redactObject`.
