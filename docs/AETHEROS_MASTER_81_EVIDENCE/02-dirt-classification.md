# §4 dirt classification — NOTHING destroyed, nothing staged, nothing committed

Method: `git status --porcelain` grouping + `git diff --ignore-all-space --stat`
(line-ending noise excluded; 1424 files still differ → real content drift).

| Category | Count | Content |
|---|---|---|
| SOURCE_CHANGE (pre-existing drift) | ~1424 tracked-modified | content drift across aetheros/ tree from prior sessions (marketplace etc.); root `.github/workflows/{desktop-build,desktop-nightly,desktop-release}.yml` carry uncommitted step improvements (e.g. split build+path-guard+builder) |
| EXPECTED_MASTER_80_CHANGE | 2 M + ~15 ?? scripts | `apps/desktop/package.json` (M, +7 desktop:* scripts), `build-all-installers.mjs` (M, retired), new `scripts/release/*` guards/preflight/validator/orchestrator (??) |
| DOCUMENTATION / EVIDENCE | ~all `docs/AETHEROS_MASTER_{79_2,80,81}_*` | prior-Master + current reports/manifests/evidence (??, intentional) |
| RELEASE_GENERATED_OUTPUT | dist-packaged/ (??), dist/, build/ (ignored) | historical artifacts b86b22f7…/1069fc6d…/214d4255… = HISTORICAL, never RC |
| Nested inert scaffolding | `aetheros/.github/workflows/*` (??) | session-generated, never executed by GitHub (root .github is live); Master-81 certification workflow PROMOTED to root, nested copy removed |
| UNKNOWN (deleted-tracked check) | `git status` D-class query returned empty on re-check | no confirmed deletions outstanding |

Remediation (requires user): decide per-category commit/stash/discard, or designate a
different release commit. Until then: RELEASE_SOURCE_NOT_CLEAN.
