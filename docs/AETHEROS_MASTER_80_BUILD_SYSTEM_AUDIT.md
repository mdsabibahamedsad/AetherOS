# AETHEROS Master 80 — Build-System Audit (inspected, not guessed)

Commit `2bdfbfd8ebcf2bb27b06f600c2beb159e723d8b1`, tree DIRTY. Date 2026-09-15.

## 1. Build entrypoints

| Entrypoint | Type | Verdict |
|---|---|---|
| `npm run dist:win` (apps/desktop) | developer build: `build` + path-guard + `builder -- --win` | KEEP (developer path, ungated by design) |
| `npm run dist:win:{nsis,msi}` | single-target developer builds | KEEP |
| `npm run desktop:release:windows` (NEW, Master 80) | canonical release: preflight→clean→npm ci→lockfile→build→builder→validate→manifest | CANONICAL (§3) |
| `scripts/build-all-installers.mjs` | legacy multi-platform builder → `release/`, npx, no gates, stale "Aetheros" naming | RETIRED (hard exit 1 + pointer, §67) |
| `npm run dist` / `dist:mac` / `dist:linux` | other platforms | OUT OF SCOPE (untouched) |

## 2. Package entrypoints / outputs

- electron-builder config: inline `build` in `apps/desktop/package.json` (no separate yml/json/config file — verified).
- `directories.output = dist-packaged` (canonical, build-owned). `release/` absent on disk (legacy dir gone; only the retired script referenced it).
- Intermediates: `dist/` (renderer, gitignored), `build/` (stamp, native-deps, bundled-python; gitignored), `win-unpacked/` inside dist-packaged (electron-builder staging).
- `dist-packaged/` is UNTRACKED (not gitignored) → its contents appear in `git status --porcelain`; release preflight therefore requires it empty/absent. Historical evidence preserved in `docs/AETHEROS_MASTER_*` manifests (immutable, never overwritten).

## 3. Cleanup mechanisms (before Master 80: NONE for dist-packaged)

No script cleaned `dist-packaged/` before build — root cause of stale accumulation. Master 80: `desktop:clean:windows` + orchestrator clean with `assertOutputDirSafe()` (§71).

## 4. Validators / manifest / hash generators

| Script | Did | Gap closed by Master 80 |
|---|---|---|
| `validate-artifacts.mjs` | naming/size/staleness + manifest cross-check, exit-coded | kept (legacy cross-check); hard gates moved to `validate-windows-release.mjs` |
| `write-artifact-manifest.mjs` (`--tag`) | per-phase manifests, HEAD_BOUND/NON_HEAD_BOUND recorded but NOT failed | kept; release manifest now canonical schema v1 via validator |
| `check-packaging-path-lengths.mjs` + 9 tests | projected-path guard, 35061 files | kept; wired into preflight (A11) + canonical build |
| `check-production-readiness.mjs` | release readiness probe | kept; out of Windows-contract scope |
| `sign-windows.mjs` | Azure/signtool or `SIGNING=BLOCKED` exit 1 | kept; verified never fakes signatures (§50) |
| `test-desktop.mjs` | installer test orchestration | kept; CI runtime probes supersede for headless |

## 5. CI build paths

- `desktop-release.yml` (`build-windows` job): `npm ci` → renderer+Electron tests → `npm run dist:win` → hash → upload. Sound; left untouched (platform matrix owner).
- `windows-desktop-certification.yml`: restructured by Master 80 into 7 jobs (preflight→test→build→validate→runtime→roundtrip→evidence), Node from `.nvmrc`, collision-safe artifact names (§34), round-trip verify (§61–62). ONE authoritative workflow (§28); no new workflow created.
- `windows-platform.yml`: unit/python/bench jobs; untouched.

## 6. Toolchain declarations (resolved §12/§14/§15)

| Item | Declared | Actual | Canonical (Master 80) |
|---|---|---|---|
| Node | root `>=20.0.0` (loose); desktop `^20.19.0 \|\| >=22.12.0`; `.nvmrc` 22.12.0; CI 22 | local 25.5.0 (satisfies desktop engines, ≠ CI) | **Node 22** (`.nvmrc` + CI + builder-26 matrix); preflight FAILs other majors; local 25.5 documented difference |
| npm | bundled | 11.8.0 local | bundled-with-canonical; version recorded per build |
| Electron packaged | `build.electronVersion` 40.9.3 (intentional pin) | win-unpacked exe FV 40.9.3 ✔ | 40.9.3; dev `^40.10.6` floats intentionally (installed 40.10.6) — documented, not unified |
| electron-builder | `^26.8.1` | installed 26.8.1 exact, repo-local | 26.8.1 via `./node_modules/.bin` (§16); preflight asserts exact |

## 7. Stale-artifact risks (all now gated)

Source-changed/artifact-not-rebuilt, old title in package, dirty tree, Node drift, unexecuted CI, historical-hash confusion, cross-phase manifest confusion, mixed-output dir, no fail-hard, no canonical command, weak source binding, six indistinguishable build kinds. Each maps to an executable guard (§82 table in contract doc).

## 8. Current mismatches (live, caught by new gates)

- `dist/index.html` title `Aetheros` vs source `AetherOS` → C07 FAIL (rebuild fixes; gate prevents silent pass).
- install-stamp `dirty=true` → B12 FAIL (clean-tree rebuild fixes).
- Local Node 25.5 vs canonical 22 → A02 FAIL (canonical toolchain fixes).
- `docs/AETHEROS_RELEASE_ARTIFACT_MANIFEST.json` pins commit `e3e9746` (older) — historical, left immutable.

## 9. Hermes references (§68)

21 hits in `scripts/`, all temp-file prefixes (`hermes-before-pack-*`, `/tmp/hermes-latency-*`) or comments. None affect build/packaging/runtime identity/artifact paths/CI. NO CHANGE (backward-compat temp names harmless; rebrand sweep explicitly out of scope).
