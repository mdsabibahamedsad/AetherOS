# AetherOS macOS Computer Use / Performance / E2E / Troubleshooting

Computer use: cua-driver native AX tree on macOS (better than Windows
OCR fallback); agent flow find→verify-enabled→act→verify-state at
application/UI/filesystem levels; coordinate fallback last. Golden
journeys (settings change, editor save, browser act, denied-permission
degradation): defined, UNEXECUTED (BLOCKED — MACOS ENVIRONMENT).

Performance: no Mac numbers claimed. Bench harness is Windows-executed;
Apple Silicon + Intel figures BLOCKED — hardware. Targets when
available: cold/warm startup, interactive, backend/agent/IPC, capture,
shutdown — median/p95/p99 with full environment record.

Troubleshooting: Gatekeeper blocks → verify signature/staple (once
signed); TCC denials → Settings links from capability model; Keychain
denials → re-prompt, never plaintext; `~/Library/Logs/AetherOS` for
diagnostics bundles (redacted). Uninstall: remove app + login item +
associations; offer Keep/Remove data; never auto-delete.
E2E: DMG→Gatekeeper→setup→Keychain→permissions→backend→agent→computer-
use→approval→artifact→notification→update→recovery→uninstall — all
BLOCKED until a Mac runner/VM exists.
