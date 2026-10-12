# AetherOS Master 76 Updater Validation (commit 2bdfbfd, win32-x64)

## State machine (§6)
15 states, guarded transitions, illegal jumps throw (update-state-machine.ts);
post-activation failure → ROLLBACK. Unit-proven (Master 70.5 suite, re-run
green 2026-09-12). Interrupted-transition recovery: downloader resumes via
Range; crash-during-install → health gate → rollback. No stuck-state path
found in audit. Minimum persisted state: staging paths + history + config
(no secrets — telemetry scrub tested).

## CLI updater chain (§5, this phase's focus)
Reproduced end-to-end in tests: manifest→version→platform→download→verify→
stage→install→health→rollback paths all green (80 tests, 5 files). Downgrade
prevention: verified by red-team (Master 70.5) + `allowDowngrade: false`
wiring. Rollback-not-downgrade: rollback restores previous-known-good through
the same verify pipeline (no bypass). Stale locks: concurrent-instance scan
prevents WinError-32 pileups (tested). Untrusted content: installer bytes are
hash+RSA-verified before staging; metadata treated as untrusted (red-team).
Redirect resistance: HTTPS-only artifact URLs; update sources are
channel-pinned, not taken from metadata. Digest-before-execution: enforced in
downloader + adapter verify.

## Windows validation (§7)
Real package BUILT (NSIS/MSI/portable, Electron 40.9.3). Unpacked app
LAUNCHED: window "Aetheros", responding, alive 25s. Installer hash + blockmap
(8953 chunks) recorded. Installer EXECUTION: BLOCKED (no clean VM, no
elevation in session). N→N+1 served update, migration, failed-update,
rollback, interrupted/corrupted/revoked/arch-mismatch on device: BLOCKED
(harness-covered only). No device claim made.

## macOS / Linux / mobile (§8/9)
No hardware/runners/certs → BLOCKED, unchanged. Linux strategy audited, not
executed (adapters + repo paths present; AppImage/deb/rpm E2E need runners).

## Security (§10/25)
Red-team green (re-run). New: will-attach-webview policy (partition allowlist
+ forced prefs, preload stripped) tested 12/12. IPC: update:* channels
validated main-side, install args allow-listed (Master 70.5, unchanged).
TOCTOU/symlink/privesc on device: UNVALIDATED (needs lab).
