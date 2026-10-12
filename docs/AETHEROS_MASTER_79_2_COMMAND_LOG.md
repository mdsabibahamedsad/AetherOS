# AETHEROS Master 79.2 — Command Log (actual executions, 2026-09-15 UTC)

Host: Windows Pro build 26200 (25H2), non-admin. Commit 2bdfbfd8ebcf2bb27b06f600c2beb159e723d8b1, tree DIRTY.

1. `git log --oneline -5` + `git rev-parse HEAD` → HEAD 2bdfbfd8ebcf2bb27b06f600c2beb159e723d8b1 ✔
2. `Get-FileHash` SHA-256 x3 → all MATCH §3 baseline ✔
3. `node scripts/release/validate-artifacts.mjs` (apps/desktop) → VALID, exit 0 ✔
4. `node scripts/release/check-packaging-path-lengths.mjs` → VALID, 35061 files, 6 absolute-only warnings, exit 0 ✔
5. `node scripts/release/check-packaging-path-lengths.test.mjs` → 9/9 PASS ✔
6. `node --test electron/*.test.cjs` (17 files) → 176/176 PASS ✔
7. MSI Property table via WindowsInstaller COM → ProductCode {77035F50-600E-49B1-851F-6E004FDBC134}, 1.0.0.0, AetherOS ✔
8. `Get-AuthenticodeSignature` x3 → NotSigned x3 (UNSIGNED) ✔ recorded
9. `Select-String` title: source `<title>AetherOS</title>` ✔; dist stale `<title>Aetheros</title>` (OLD_ARTIFACT_KNOWN_ISSUE); asar AetherOS x140 / Aetheros x93 (identifiers) ✔
10. win-unpacked inspection: AetherOS.exe present, ProductName=AetherOS, FV=40.9.3 ✔
11. Host launch probe: AetherOS.exe started (pid 4936), alive at 15s, killed, process table clean ✔ INFORMATIONAL
12. `node scripts/security/audit-security.mjs` → 50/100 (12/24), exit 0 ✔ recorded
13. `node scripts/security/check-secrets.mjs` → exit 1 (test-fixture hits) ✔ recorded
14. `node scripts/security/audit-dependencies.mjs` → 32 vulns (21 high, 1 critical), exit 2 ✔ recorded
15. `build.electronVersion` → 40.9.3 ✔ (do NOT modify)
16. OS/privilege: build 26200, Administrators deny-only (non-admin) ✔; Sandbox absent ✔
17. Created `.github/workflows/windows-desktop-certification.yml` (new file) ✔
18. `gh auth status` → token invalid → CI dispatch NOT possible from dev host ✔ recorded (no CI run)
19. Wrote docs: CI manifest, matrix, blocked tests, command log, CI cert, final manifest, final cert, EVIDENCE/ (12 files) ✔

NOT executed (no capability): VM provisioning (no hypervisor), CI dispatch (bad gh token),
installer install/uninstall on dev host (deliberately avoided — dirty non-admin host ≠ clean env),
rebuild of artifacts (not required; historical hashes preserved per §15).
No product architecture modified. §2 fixes unregressed (no changes to manifest validator, path guard, title source, Electron pin).
