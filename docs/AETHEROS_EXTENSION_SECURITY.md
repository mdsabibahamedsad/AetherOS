# Extension Security (Master 44)

## Boundary truth table

| Layer | Mechanism | Status |
|---|---|---|
| Renderer → backend | Typed `extension.*` IPC, server-side validation | ENFORCED |
| Extension code → Node/IPC | Never loaded in renderer; no ipcRenderer/Node granted | ENFORCED |
| OS process isolation | Jailed subprocess (stripped env, cwd jail, no shell, timeout) for smoke runs | PARTIAL |
| OS filesystem/network | Capability-layer enforcement (scoped grants) | PARTIAL |
| Kernel namespaces/seccomp/Seatbelt | Not claimed | NOT IMPLEMENTED |

"PARTIAL" is explicit in `SANDBOX_BOUNDARY`, surfaced to UI, and recorded
in the certification report. No full-sandbox claim is made anywhere.

## Enforcement points (runtime, not UI)

PermissionEngine.check on every fs/net/secret/tool action; ToolAuthorizer
(swam) + autonomy caps for agents/automation; approval gates for HIGH/
CRITICAL; quarantine revokes contexts + grants + MCP + tools.

## Content trust

Skill instructions, MCP descriptions, READMEs, manifests, remote indexes
are untrusted data: injection scan at install + invocation; override
phrases blocked; policy can never be redefined by content (proven by
adversarial tests).

## Secrets

SecretBroker only: grant + user approval + registered provider per scope.
Raw stores, .env, cookies, refresh tokens never attached. Logs/traces
pass through secret redaction.

## Supply chain

SHA-256 per file + manifest + package digests; Ed25519 publisher/repo
signatures with expiry + revocation + rotation (new key = new record);
pinned/locked deps; cycle/confusion/mismatch fail closed; SBOM =
integrity.json + manifest provenance fields (no separate SPDX claim).

## Scans

Static: executables, shell, exfil, obfuscation, persistence, override,
traversal, bombs, oversized → PASS/WARN/BLOCK. UI wording is "static
analysis passed", never "safe". Dynamic: isolated smoke run with
observed exit/wall/RSS/stdout; only executed runs reported.
