# AetherOS Windows Security

Enforced: sandboxed renderer, context isolation, no Node integration,
single-namespace preload, capped file IPC, `safeStorage`/DPAPI secrets
with fail-closed behavior, approval-gated computer-use/side-effects,
audit events on trust/delegation changes, no wildcard IPC found.

Windows-specific rules: never concatenate untrusted input into shell
strings (spawn argv / parameter binding); resolve canonical paths and
treat symlinks/junctions/UNC as untrusted (`resolveDirectoryForIpc`
tested); no secrets in command lines, notifications, logs, or crash
reports; localhost services must not assume loopback == trusted.

Threats explicitly NOT mitigated here: unsigned distribution
(SmartScreen/Defender reputation — see SIGNING), no UIA boundary
(computer-use is SendInput + OCR; keep approval gates on), no tray/lock
screen agent control. DLL search-order/PATH hijacking: bundled backend
runs from the package dir; do not add user-writable dirs to PATH.
No security control is disabled as a workaround anywhere in this design.
