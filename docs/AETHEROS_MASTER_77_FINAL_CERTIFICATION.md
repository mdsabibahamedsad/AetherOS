# AetherOS Master 77 — Final Certification (2026-09-13)

Certification: **AETHEROS_DESKTOP_LINUX_BLOCKED**

Reason: P0 blockers remain open — Linux AppImage/DEB/RPM do not exist (no runner executed);
MSI/portable artifacts are not HEAD-bound (WiX MAX_PATH blocks local MSI rebuild);
no clean-VM install/launch evidence exists for any artifact. Per §78, CERTIFIED requires actual
Linux artifacts + installation evidence + launch evidence; none can be honestly claimed.

## What was actually built

- `AetherOS-1.0.0-win-x64.exe` (195,739,994 bytes, sha256
  `87091be0…ebc0dedfa1f68`) — fresh 2026-09-13 from HEAD via `npm run dist:win:nsis`, exit 0.
- `AetherOS-1.0.0-win-x64.exe.blockmap` (202,557 bytes, `37c1e661…`) — same invocation.
- Pre-existing `…-win-x64.msi` (196,571,899, `6fe65eb4…`) and `…-portable.exe` (187,240,131,
  `cce16c07…`) — integrity VALID, retained, not rebuilt.

## Tests actually executed

typecheck PASS · Electron platform tests 176/176 PASS · `dist:linux:validate` VALID ·
`release:validate-artifacts` VALID (4-entry manifest cross-check) · fresh-binary spawn probe
(alive 20s, cleaned) · full `dist:win` FAILED at WiX LGHT0103 (documented, artifacts unharmed).

## Install / launch / update actually executed

None to completion. Install: BLOCKED (VM). Launch: UNVERIFIED (spawn-only). Update/rollback:
NOT_IMPLEMENTED (no channel) + BLOCKED (no VM). Signing: BLOCKED/UNSIGNED. SBOM/provenance:
CI-only, BLOCKED locally.

## Changed files (source)

- `.github/workflows/desktop-build.yml`, `.github/workflows/desktop-nightly.yml` (stale upload path)
- `apps/desktop/scripts/test-desktop.mjs` (stale artifact dir)
- `apps/desktop/scripts/release/validate-artifacts.mjs` (new) + `apps/desktop/package.json` (3 scripts)
- `docs/AETHEROS_MASTER_77_*` (12 docs + `EVIDENCE/`)

## Exact next actions (priority order)

1. Run `desktop-release.yml` `build-linux` on ubuntu-latest → AppImage/deb/rpm + hashes + SBOM.
2. Rebuild MSI from a short checkout path (or fix long-path handling) → HEAD-bound MSI;
   rebuild portable alongside.
3. Clean-VM Windows matrix (NSIS + MSI) and Linux matrix (AppImage/deb/rpm, GNOME + KDE, X11 + Wayland).
4. Decide product position on auto-update; if promised, implement channel + feed + signing, then
   fake-server update/rollback tests.
5. Add signing certs to CI; enable provenance attestation verification.
6. Re-run this certification checklist; only then CERTIFIED or BETA_CERTIFIED is claimable.

NEXT_PHASE_RECOMMENDATION = "Proceed to Master 78 only after Desktop/Linux P0 blockers are closed —
Linux artifacts built in CI, HEAD-bound MSI/portable produced, and clean-VM install evidence recorded."
