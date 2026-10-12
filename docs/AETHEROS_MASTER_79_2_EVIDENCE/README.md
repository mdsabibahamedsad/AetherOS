# Master 79.2 evidence index

All files in this directory are transcriptions of ACTUAL command output
executed on the developer host on 2026-09-15 (UTC). Nothing is fabricated.

| File | Source command | Result |
|---|---|---|
| `environment.txt` | node/npm versions, git HEAD, OS build, privilege check | recorded |
| `hashes.txt` | `Get-FileHash` SHA-256 of 3 Windows artifacts | MATCH Master 78A baseline |
| `validate-artifacts.log` | `node scripts/release/validate-artifacts.mjs` | VALID, exit 0 |
| `path-lengths.log` | `node scripts/release/check-packaging-path-lengths.mjs` | VALID 35061 files, 6 absolute-only warnings |
| `path-guard-tests.log` | `node scripts/release/check-packaging-path-lengths.test.mjs` | 9/9 PASS |
| `electron-tests.log` | `node --test electron/*.test.cjs` (17 files) | 176/176 PASS |
| `msi-properties.txt` | WindowsInstaller COM DB Property table | ProductCode/Version/Name recorded |
| `authenticode.txt` | `Get-AuthenticodeSignature` x3 | NotSigned x3 (UNSIGNED) |
| `title-source.txt` | `Select-String` on index.html + dist + asar probe | source=AetherOS; dist stale + asar mixed (OLD_ARTIFACT_KNOWN_ISSUE) |
| `host-launch-probe.txt` | launch win-unpacked AetherOS.exe, 15s wait, kill | started, required kill, cleaned |
| `security-static.txt` | audit-security / check-secrets / audit-dependencies | score 50/100; secrets exit 1 (test-fixture hits); deps 32 vulns |
| `msi/` | verbose msiexec logs | CI-only; empty until a CI run executes |

Host-side evidence is NOT clean-environment evidence (§14).
CI-run evidence is appended here only after
`.github/workflows/windows-desktop-certification.yml` actually executes.
