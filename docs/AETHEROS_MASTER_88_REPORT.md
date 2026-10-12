# AetherOS Master 88 Report — Private Source → Signed Build → Public Website Distribution

> AetherOS source remains private. Public desktop distribution is provided through the AetherOS website/distribution infrastructure. GitHub repository visibility was not changed.

## 1. Starting state

Master 87: packaging/SBOM/integrity green; signing, notarization, provenance, clean-VM
owner-blocked; no code changes. Master 88 is a focused architecture implementation, not a
re-certification: closed areas (packaging pipeline, Python provisioning, SBOM, integrity,
test baselines) were not reopened.

## 2. IMPLEMENTED

- **Distribution abstraction** (`website/src/lib/distribution.ts`): manifest types,
  allowlisted `resolveArtifact()`, base-URL-pinned `artifactUrl()`, strict
  `validateManifest()`. URLs never come from user input.
- **Version manifest** (`website/static/api/releases/1.0.0.json` + `latest.json`,
  schema v1): 8 artifacts with real filenames, SHA-256, sizes; URLs on the
  project-established `https://releases.aetheros.com/desktop/<version>/<file>` scheme;
  `signed=false`, `productionReady=false`; sourceCommit + workflowRun embedded.
- **Generator** (`website/scripts/generate-download-manifest.mjs`): verified inputs →
  public manifest, fails closed on any bad/missing data; hooked into `prebuild.mjs`.
- **Verified inputs** (`website/scripts/release-inputs/1.0.0.json`): checked-in real
  Master 85/86 values with provenance note (kept beside the script: the repo gitignores
  `website/data/`).
- **Download page** (`website/src/pages/download.tsx`, route `/docs/download`):
  platform cards (Windows EXE/MSI/Portable, macOS DMG/ZIP, Linux AppImage/DEB/RPM),
  version/arch/size/SHA-256 display, copy-hash, per-OS verify instructions, OS
  highlighting, honest "unsigned pre-production" badge, pending state when the manifest
  is absent. Discoverable via a new link in `website/docs/user-guide/desktop.md`.
- **Atomic publish script** (`website/scripts/publish-distribution.mjs`): implements the
  §18 gate sequence; dry-run default; `--require-signatures/--require-provenance` hard
  gates; manifest published last; `--live` refuses without owner storage + CI context.
- **`production` GitHub environment**: created (empty, no secrets — none exist).

## 2b. IMPLEMENTED (this execution — updater/distribution alignment)

- **Updater endpoint alignment** (`apps/desktop/src/updater/update-manager.ts`):
  the client previously pointed at unregistered host
  `https://updates.aetheros.com/api/v1/{platform}/{arch}/{channel}` with no
  `/updates` prefix — matching nothing the update server serves. It now uses
  `{AETHEROS_UPDATE_BASE_URL}/updates/{platform}/{arch}/{channel}` with default
  base `https://releases.aetheros.com`, exactly the routes served by
  `createUpdateRequestHandler()` in `services/update/update-server.ts`.
  `AETHEROS_UPDATE_BASE_URL` override provides the staging/local-harness
  channel (§32–33); the app still contains zero credentials (§29, grep-verified).
- **Version-consistency gate** (`.github/workflows/update-release.yml`, validate
  job): release stops unless resolved version == root `package.json` version ==
  `apps/desktop/package.json` version — the §23
  tag = package = app = manifest invariant, enforced before any build/publish.
- **No duplicate update system (§37):** verified the custom signed-manifest
  updater (`src/updater/` + `services/update/`) is the single authoritative
  update implementation — no `electron-updater`/`autoUpdater`/`setFeedURL` and no
  `latest*.yml` surface anywhere in `apps/desktop`. Nothing rewritten; the
  existing updater was integrated with the distribution origin instead.
- **No push-to-main publishing (§22):** verified both release workflows trigger
  only on version tags (`v*.*.*`) or manual `workflow_dispatch` — normal
  `git push` remains source-backup-only (§2 Event A vs Event B).

## 3. VERIFIED

- Updater vitest suite (`apps/desktop` `src/updater`): **6 files / 37 tests PASS**.
- `apps/desktop` strict typecheck (`tsc -p . --noEmit`): **clean**, covering the
  endpoint change above.
- `apps/desktop/electron/update-remote.test.cjs`: **6/6 PASS**.
- Manifest generator re-run from verified inputs: deterministic 8-artifact
  manifest (`signed=false`, `productionReady=false`).
- Secret scan: no `GH_TOKEN`/`GITHUB_TOKEN`/`AWS_*`/`R2_TOKEN`/private keys/
  `api.github.com` in `apps/desktop/src/updater/` or `apps/desktop/electron/`.
- `npm run test:distribution`: **11/11 PASS** (generation, fail-closed, allowlist,
  traversal, publish gates, secret scan, no-input-URL).
- `distribution.ts`: strict `tsc` clean. Download page: isolated strict `tsc` clean
  (caught + fixed a real `{filename}` JSX defect).
- Prebuild hook regenerates the manifest; generator + publish dry-run executed.
- Artifact URLs validated against the release asset record; no private hosts/tokens.
- Pre-existing failures documented as NOT regressions: website `tsc -p .` TS5101
  (proven identical without new files), `docusaurus build` sidebar failure (missing
  python3 for skills extraction on this host), prebuild python skips.

## 4. OWNER-BLOCKED

- `SIGNING_CREDENTIALS = OWNER_BLOCKED` (no Windows/Apple credentials; nothing signed).
- Real production upload (no storage backend configured; publish script stops at boundary).
- Reviewer gating on the `production` environment (owner chooses reviewers).
- Storage provisioning (public-read/private-write immutable prefix + publish-only CI identity).

## 5. PLAN-BLOCKED

- `PROVENANCE = BLOCKED_BY_REPOSITORY_PLAN_CONFIGURATION` (repo stays private per
  permanent requirement; existing attestation workflow preserved untouched).

## 6. ENVIRONMENT-BLOCKED

- `CLEAN_VM = BLOCKED_BY_ENVIRONMENT` (unchanged; no clean machines from this work).

## 7. Final certification

**`AETHEROS_MASTER_88_DISTRIBUTION_ARCHITECTURE_READY`** and
**`AETHEROS_1_0_PRODUCTION_BLOCKED`** (owner credentials + signatures + clean-VM still
outstanding; the website never advertises the unsigned artifacts as production-ready).
No fourth category, no fake green, no repeated loop.
