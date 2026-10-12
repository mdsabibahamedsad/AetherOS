# AetherOS Beta Release Runbook (Master 74)

Beta: **1.1.0-beta.1** · releaseId `aetheros-1.1.0-beta.1` · commit `2bdfbfd` · channel `beta`.

## Pipeline

1. **Freeze** — cut RC with `services/update/scripts/rc-manifest.mjs`. Inputs
   frozen at `frozenAt`. Any change → new RC version, never mutate.
2. **Audit** — `git status` clean on release paths; record commit in RC.
3. **Test** — `npm run test:ui -- --run src/release/__tests__ src/updater/__tests__`
   (46 tests). Failing suite → RC tool refuses to freeze (proven in evidence).
4. **Security** — `npm run security:audit`, `security:deps`, `security:secrets`
   in `apps/desktop`. Red-team manifest suite in `src/updater/__tests__/`.
5. **Performance** — `comparePerf()` in `src/release/beta-gates.ts`; thresholds
   explicit; nulls → UNVERIFIED, never pass.
6. **Signing** — `sign-windows.mjs` / `verify-notarization.mjs`. No creds →
   SIGNING=BLOCKED, pipeline stops. Never ship unsigned.
7. **SBOM** — `sbom.spdx.json` required; RC refuses to freeze without it.
8. **Provenance** — `actions/attest-build-provenance` in `update-release.yml`.
9. **Attestation** — verify before publish (`verify-manifest.mjs`).
10. **RC** — immutable JSON in `dist-publish/rc/<releaseId>.json`.
11. **Internal beta** — install/launch/agent/update/rollback on available machines.
12. **Canary** — `canary-install.mjs` (hash + signature). Start rollout at
    `maxRolloutStartPct` (beta: 10%).
13. **Limited beta** — expand 10% → 25% → 50% only on `evaluateRolloutGate()=PASS`.
    UNVERIFIED or HOLD → do not expand. ROLLBACK → revoke + revert.
14. **Health review** — crash/startup/update/auth + security/user signals.
15. **Expanded beta** — 100% only after sustained PASS.
16. **Beta exit review** — `evaluateBetaExit()` all 10 categories PASS with evidence.

## Halts and revocation

- Pause: `set-rollout.mjs --percentage <n>`; kill: `--kill`.
- Revoke: `revoke-release.mjs <release|artifact|channel|version>` (needs
  `UPDATE_ADMIN_URL` + `UPDATE_ADMIN_TOKEN` + `RELEASE_ID`).
- Rollback: promote previous-known-good; clients verify it like any release.
- Data rollback is NEVER automatic-destructive (Master 61 checkpoints first).

## Hotfix

detect → branch → fix → test → security review → build → sign → SBOM →
provenance → attest → verify → deploy → monitor. New version + digest always.
