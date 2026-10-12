# MASTER 79.1 EXECUTION-2 — Report (deltas vs Master 79)

Original Master 79 files are preserved untouched; this is the versioned
second-execution record (§32).

## Source changes made (4 files, all release tooling + 1 branding line)

1. `apps/desktop/scripts/release/check-packaging-path-lengths.mjs` (§17):
   evaluates the PROJECTED production path
   (`C:\Program Files\AetherOS\` + package-relative path; bundled-python
   content mapped under `resources/`) as the blocking check; absolute-only
   excess is a non-blocking warning; `__msi-x64` still evaluated absolute
   (it IS the WiX staging input); new `--strict` / `--install-prefix` flags.
2. `apps/desktop/scripts/release/check-packaging-path-lengths.test.mjs`:
   4 new tests (prefix-only warning, projected overflow still fails,
   target-base mapping, adapted longest-first).
3. `apps/desktop/scripts/release/write-artifact-manifest.mjs` (§19):
   `--tag MASTER_##` (validated); each phase writes its own manifest.
4. `apps/desktop/scripts/release/validate-artifacts.mjs` (§19):
   preference M79 → M78 → M77 + prints the manifest path used.
5. `apps/desktop/index.html:11` (§26): `<title>Aetheros</title>` →
   `<title>AetherOS</title>`. Remaining `Aetheros` strings are internal
   identifiers (IPC `aetheros:*` channels, `aetheros_cli` module, comments);
   tray labels already `AetherOS`. Packaged artifacts still carry the old
   renderer title until the clean-tree release rebuild (§22 deferred).

## New generated files

- `docs/AETHEROS_MASTER_79_RELEASE_ARTIFACT_MANIFEST.json` (7 artifacts,
  headBound=true, LOCAL_SOURCE_BINDING, win hashes == §10 baselines).
- `docs/AETHEROS_MASTER_79_ARTIFACT_CHECKSUMS.txt`.
- Removed: untracked `AETHEROS_MASTER_78_*_MANIFEST/CHECKSUMS` byproducts
  (never committed; original content already superseded — see incident note).

## Incident note (honesty record)

During Master 79, `write-artifact-manifest.mjs --help` was invoked; the
script has no `--help` handling and EXECUTED, overwriting the untracked
M78 manifest with current-dist hashes at 2026-09-15T04:11:14Z. This explains
why a later re-run of the validator passed: the "stale manifest" INVALID
recorded in Master 79 was genuine AT MEASUREMENT TIME (validator used the
4-entry M77 fallback and failed 11 checks). The M79 manifest above was
regenerated deliberately via the new `--tag` path; hashes are computed from
artifacts, never hand-edited.

## Verification results (§27)

- `check-packaging-path-lengths.mjs`: VALID, 35061 files; 6 absolute-only
  warnings (elevenlabs/mistralai, max PROJ 218 < 240) → §17 verdict B
  (checkout-prefix artifacts, NOT production paths). Runtime import on a
  clean VM still UNVERIFIED (§18 — no VM).
- Guard tests: 9/9 PASS. Electron platform tests: 176/176 PASS (post-change).
- `validate-artifacts.mjs`: VALID, 7 entries, exit 0 (against M79 manifest).
- Full pytest / renderer vitest: not run (renderer change is a static title
  string with no test surface; full suites remain a pre-release gate).

## §20 dirty-tree classification (measured, not modified)

`git status --porcelain`: 1787 modified tracked, 13 deleted, 963 untracked.
My session added: 8 Master-79 doc paths + 5 source edits + 2 M79 manifest
files (−2 removed M78 byproducts). Everything else pre-existed (Master 78A
already reported dirty). No reset/clean/stash performed (§96).

## §21/§22 clean-tree workspace + rebuild: DEFERRED

A `git worktree` clean checkout plus full electron rebuild (npm ci, tsc,
vite, python bundling, electron-builder ×3 targets) was evaluated and
deferred: it does not unblock anything without a clean TEST environment,
and would produce yet another local dirty-tree-equivalent artifact set.
Documented next action: clean-tree rebuild on CI (Node 22, §24 authoritative)
when a test VM is available.

## §24/§25 parity answers

- Node: CI (22) is authoritative for release; local 25.5.0 builds are
  dev-only. Reproducibility gap stands (P1).
- Electron: `build.electronVersion: 40.9.3` is an explicit config pin
  (only occurrence in repo besides lockfile resolution); dev `^40.10.6`
  floats. Treated as INTENTIONAL per 78A; no code change. Rationale comment
  still absent in repo — recommended follow-up, not done here.
