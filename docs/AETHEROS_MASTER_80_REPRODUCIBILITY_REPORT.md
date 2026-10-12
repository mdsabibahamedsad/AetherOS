# AETHEROS Master 80 — Reproducibility Report (§63–§64)

Claimed level: **Level 1 — source/toolchain identity recorded.** No higher level is
claimed because no higher level has been demonstrated.

| Level | Requirement | Status | Evidence |
|---|---|---|---|
| L0 | build succeeds | NOT_RUN (local release blocked by dirty tree + Node 25; CI owns rebuild) | 01-preflight.json PREFLIGHT_FAIL |
| L1 | source/toolchain identity recorded | PASS (mechanism exists + exercised) | 09-manifest.json schema v1: commit, tree, node/npm/electron/builder, buildId, manifestSha256 |
| L2 | clean-build artifact validated | PASS (mechanism exists; live run correctly FAILs dirty/stale fixtures) | 12-validation-status.json (B12+C07 FAIL = gates working, not a clean-build PASS) |
| L3 | independent rebuild matches identity | NOT_RUN | requires CI build + roundtrip job |
| L4 | bit-for-bit demonstrated | UNVERIFIED (not attempted; timestamps in Electron/NSIS/MSI outputs make it unlikely) | — |

Deterministic: artifact names, electron-builder config, toolchain pins, manifest schema,
guard verdicts. Non-deterministic (documented, not forced): embedded timestamps, compression
ordering, code-signing timestamps. No artifact was modified to force identical hashes (§64).

Cache policy (§65): npm cache only; outputs rebuilt + revalidated every release.
Cache-corruption recovery (§66): clean-output guarantee + full revalidation make a corrupt
cache observable (build fails or gates fail), never silently shippable; `desktop:clean:windows`
+ fresh `npm ci` is the documented recovery.
