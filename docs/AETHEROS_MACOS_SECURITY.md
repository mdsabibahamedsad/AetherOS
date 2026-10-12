# AetherOS macOS Security / Permissions / Keychain / Accessibility

Security: Electron hardening (Master 64 verified), minimal entitlements
(`allow-jit`, `allow-unsigned-executable-memory`, `disable-library-
validation` — Electron-required, justified; audio-input for voice;
NO `get-task-allow` — enforced by `macos_entitlements_audit.py` in CI),
DYLD hygiene (no user-writable PATH additions), Apple Events only via
validated structured calls with target allowlist + approval + audit.

Permissions (`macos_tcc.py`): accessibility/screenRecording/microphone/
camera/automation/filesFolders/fullDisk with NOT_DETERMINED default,
request-only-when-invoked, Settings deep links, graceful degradation —
never prompt spam, never fake grants. Accessibility tree: normalized
`AXElement` (`ax.py`), control requires paired read scope, AetherOS-only
by default. Keychain: service/account model, access scopes, rotation/
deletion/migration handling, locked/denied surfaced, NO plaintext
fallback ever (`PlaintextFallbackForbidden`). Live TCC/Keychain/AX:
BLOCKED — MACOS ENVIRONMENT.
