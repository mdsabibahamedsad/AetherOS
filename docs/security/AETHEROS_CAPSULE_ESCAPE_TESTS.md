# AetherOS Capsule Escape Tests

Executable: `tests/kernel/test_agent_capsule_security.py`
(§112 probes), `test_agent_capsule.py` (filesystem behavior).

## Filesystem escapes (§19) — all must DENY

`../host`, `../../etc/passwd`, `/etc/passwd`, `/`, `C:\Windows\System32`,
`C:/secret`, `\\server\share`, `\\?\C:\secret`, `..\..\secret`,
`workspace/../../outside`, null byte, `CON`, `NUL`, `AUX`,
`file:stream` (ADS), `\\.\C:` (device path) — plus a live symlink test
pointing outside the root (skipped where the OS forbids symlinks).

Documented semantic: unknown absolute paths (e.g. `/etc/passwd`)
virtualize into capsule-private storage (`<root>/etc/passwd`) — contained,
never the host file. The test asserts containment (`startswith(root)`,
`!= host path`).

## Network escapes (§21) — all must BLOCK

Metadata (`169.254.169.254`, `100.100.100.200`), localhost/loopback
(name, `127.0.0.1`, `::1`), decimal int (`2130706433`), hex int
(`0x7f000001`), dotted hex (`0x7f.0.0.1`), octal (`0177.0.0.1`),
link-local IPv6 (`fd00::1`), wrong schemes (`ftp:`, `file:`), embedded
credentials. Live check: `network.request` to the metadata endpoint
through a started capsule raises `PermissionError`.

## Process / credential escapes (§23)

No host process access, no debugger attach, no privilege escalation, no
shell for untrusted profiles (policy flags, enforced at admission and
surfaced in `process_policy`). Credential theft: cross-capsule binding
use denied; expired bindings denied; revoked bindings denied.

## Prompt injection (§113)

Payloads shaped as web/PDF/email/MCP/A2A/terminal/repo/README/OCR/
screenshot/audio/QR/device instructions grant zero authority:
post-admission capabilities remain within the profile default set, with
no admin/mount/elevated entries. Tool-input screening defers to the
kernel security boundary.

## Malicious agent (§114)

Untrusted-profile agent attempts escalation, exfiltration, secret use,
spawn, and network egress — every attempt BLOCKED. Spawn explosion
stopped by child quota. Denied attempts leave hash-chained receipts
(tamper-evidence verified link-by-link).
