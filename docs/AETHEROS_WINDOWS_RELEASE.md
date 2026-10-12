# AetherOS Windows Release Process

1. Version bump (`apps/desktop/package.json` + backend `pyproject.toml`
   `0.16.0` — keep in sync; web `0.0.0` is a private package).
2. Push tag → `desktop-release.yml` builds NSIS/MSI/portable on
   `windows-latest`, writes SHA256, uploads artifacts + release.
3. Fill `AETHEROS_WINDOWS_RELEASE_MANIFEST.json` with VERIFIED values only.
4. Publish notes incl. known limitations; never claim signed/Store/E2E
   without evidence.
5. Rollback = previous release artifacts (no in-app rollback exists).

Gates (P0): app launches, backend healthy, IPC secure defaults intact,
installer/uninstaller verified on a clean VM, no critical vulns, no
data-loss bugs, artifacts reproducible with matching hashes.
MSIX/Store decision: NOT pursued — direct NSIS/MSI/portable is the
supported model; Store submission is BLOCKED (account/certification).
