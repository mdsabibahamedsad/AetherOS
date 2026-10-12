# AetherOS Master 84D Report — CI Python Environment Provisioning + Cross-Platform Packaging Recovery

## 1. Previous failed run
- Run **35124008779** (#9), `https://github.com/sabib360/AetherOS/actions/runs/35124008779`
- Head SHA `b5870ea6801b8a6d105342d104b45ac938b83a95`, branch `release/aetheros-1.0.0-rc-84c`
- Historical failure evidence ONLY. Never reused as success evidence.

## 2. Failure
`bundle-python.cjs` threw `Cannot find a working virtual environment to bundle at <repo>/aetheros/.venv`
on Windows, macOS, and Linux (identical error class on all three runners).

## 3. Root cause
Workflow omission, not application defect: `.github/workflows/desktop-release.yml` never created
`aetheros/.venv` — no `setup-uv`, no Python install, no `uv sync` before `npm run build`.
(A bonus finding: macOS runners ship system Python 3.14, outside the bundler's supported 3.11–3.13.)

## 4. Python contract
- `requires-python = ">=3.11,<3.14"` (`aetheros/pyproject.toml`); bundler supports 3.11–3.13
- Package manager: **uv** (`aetheros/uv.lock` present; lock verified fresh via `uv lock --check`, 219 packages)
- Authoritative pattern reused from `aetheros/.github/workflows/tests.yml`:
  `astral-sh/setup-uv@d4b2f3b6...` (v5) → `uv python install 3.11` → `uv sync`
- CI command: `uv sync --locked --python 3.11 --extra all` (dev excluded to avoid bundle bloat;
  matrix excluded — Linux-only native wheels, see pyproject `[all]` policy comment)
- Full contract: `aetheros/docs/AETHEROS_MASTER_84D_EVIDENCE/01-python-contract.json`

## 5. Workflow fix (all in `.github/workflows/desktop-release.yml` unless noted)
1. **Commit `910a66b`** — Python/uv provisioning (install uv, Python 3.11, locked sync, node-based
   cross-platform `.venv` interpreter verification) in all three build jobs, before tests/packaging.
2. **Commit `27d3ca1`** — `--publish never` on all builder invocations (electron-builder implicit CI
   publish needs `GH_TOKEN`; releases are uploaded by dedicated `softprops/action-gh-release` steps).
3. **Commit `ee0e33d`** — bundler POSIX copy fix (`aetheros/apps/desktop/scripts/bundle-python.cjs`:
   materialize file symlinks, skip dir links; fixes macOS `codesign --strict` rejection of absolute
   uv-venv symlinks) + workspace-relative paths for SBOM/upload steps (`uses:` steps ignore
   `defaults.run.working-directory`).
4. **Commit `2d72b42`** — macOS targets scoped to `dmg zip` (the `pkg` target references installer
   files that exist nowhere in the repo — dead config) + Windows `.blockmap` sidecar added to uploads
   (the SHA manifest lists it; integrity check fails closed without it).

## 6. Local verification
- `bundle-python.cjs`: exit 0, 270.7 MB bundle, smoke test `pydantic 2.13.4` (before AND after the copy fix)
- Typecheck PASS; Electron 176/176 PASS; Vitest 119 files / 814 tests PASS; release guards 22/22 PASS;
  win path guard VALID (16517 paths); linux packaging VALID
- `uv 0.12.15`, `uv python install 3.11` → 3.11.15, `uv lock --check` clean
- Full clean `uv sync` intentionally left to CI fresh runners (documented limitation)

## 7. New commits (fast-forward, no history rewrite, `origin/main` untouched)
- `910a66b926f686d362ebd842eacb7ac7f91a9a88` (Python provisioning)
- `27d3ca1002ee2552eebcbb114bbc9eb061a92dae` (publish fix)
- `ee0e33da02af0840cfba3573824be96a930d229c` (symlink + path fixes)
- `2d72b423d197afb57ad641a0b15eed68230da25e` (mac targets + blockmap)

## 8. Remote branch
`origin/release/aetheros-1.0.0-rc-84c == 2d72b42` (verified via `git ls-remote` after every push).

## 9. New CI runs
- #10 `35177617226` (910a66b): Python provisioning PASS everywhere; exposed publish defect
- #11 `35178702673` (27d3ca1): publish fix verified; exposed symlink + SBOM-path defects
- #12 `35179993397` (ee0e33d): Linux FULLY GREEN; exposed pkg-target + blockmap defects
- **Decisive #13 `35181165305` (2d72b42): SUCCESS — all jobs green.**
  `https://github.com/sabib360/AetherOS/actions/runs/35181165305`

## 10. CI head SHA
`2d72b42 == 2d72b423d197afb57ad641a0b15eed68230da25e` — PASS.

## 11. bundle-python
PASS on Windows, macOS (3.11.16), Linux (3.11.16). Smoke: `pydantic 2.13.4`.

## 12. Packaging
- Windows: `AetherOS-1.0.0-win-x64.exe` (166 MB), `.msi` (169 MB), `-portable.exe` (166 MB), `.blockmap`
- Linux: `.AppImage` (203 MB), `.deb` (172 MB), `.rpm` (139 MB)
- macOS: `-macOS-arm64.dmg` (204 MB), `-macOS-arm64.zip` (202 MB) — arm64 only (host-arch build)
- Integrity check (`sha256sum -c` on downloaded bytes): Linux + Windows PASS

## 13. Hashes
Build-recorded SHA-256 in `*-artifacts.sha256` (see `08`/`09` evidence). GitHub artifact digests recorded.
Exception (pre-existing): `win-x64-portable.exe` is not hashed by the workflow's SHA glob — follow-up.

## 14. SBOM
PASS. SPDX-2.3: 232 packages (linux), 291 (windows). Validated by local parse of release assets.

## 15. Provenance
BLOCKED — no provenance step configured in `desktop-release.yml`.

## 16. Attestation
BLOCKED — no `attest-build-provenance` step (`attestations: write` permission present but unused).

## 17. Signing
SIGNING_BLOCKED_BY_CONFIGURATION — no signing secrets wired in this workflow; macOS ad-hoc signed
(`CODE_SIGNING_ALLOWED=NO`); Windows installers unsigned. Nothing faked.

## 18. Clean VM
BLOCKED — GitHub runners prove packaging only; separate clean-VM validation still required.

## 19. Secondary workflow
SECONDARY_WORKFLOW_BLOCKER — Desktop Build runs #8/#9/#10 fail on eslint (`no-control-regex` in
hardening.cjs + `curly`). Untouched: Desktop Release does not depend on it.

## 20. Final certification
**CI_PACKAGING_GREEN** (production remains **AETHEROS_1_0_PRODUCTION_BLOCKED** pending
signing, attestation/provenance, and clean-VM validation).
