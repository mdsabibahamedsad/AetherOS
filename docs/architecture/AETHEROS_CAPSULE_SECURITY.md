# AetherOS Capsule Security

Implementation: `kernel/core/hypervisor/{guards,isolation,secrets,risk}.py`,
`security_boundary.py`, `policy_engine.py`.

## Deny-by-default (§16)

Inside a capsule filesystem → DENY, network → DENY, device → DENY,
process → DENY, secret → DENY, browser → DENY, computer → DENY — then the
profile + admission grant back exactly the declared set. The manifest gate
in `invoke()` enforces it on every call.

## Isolation levels (§7) — what 1.0 actually provides

| Level | Provider | Status on reference host |
|---|---|---|
| LEVEL_0 process isolation | `native_process` | SUPPORTED (scrubbed env, cwd jail, no handle inheritance) |
| LEVEL_1 sandboxed process | `windows_native` (Job Objects) | SUPPORTED where probe succeeds |
| LEVEL_1 sandboxed process | `sandboxed_process` / firejail / Windows Sandbox | REQUIRES_CONFIGURATION unless detected |
| LEVEL_2 container | `container` (docker/podman) | SUPPORTED only with reachable daemon, else REQUIRES_CONFIGURATION/UNAVAILABLE |
| LEVEL_3 VM | `vm` | UNAVAILABLE in 1.0 — never claimed |
| LEVEL_4 dedicated host | — | UNAVAILABLE — never claimed |

`aetheros capsule isolation` prints the live detection table.
Profile floors (e.g. `untrusted` → LEVEL_1) are enforced at provisioning:
a capsule is refused rather than silently downgraded.

## Path-escape defense (§19)

`validate_capsule_path()` rejects `../` traversal (lexical + containment),
absolute host paths (POSIX + drive-absolute), UNC (`\\server\share`),
device paths (`\\.\`, `\\?\`, CON/PRN/AUX/NUL/COM/LPT), NTFS ADS suffixes,
null bytes, and symlink/junction/reparse escapes (deepest-existing-prefix
resolution must stay inside the root). Mount sources are validated by
`validate_mount_host_path()`; SECRET mounts are unrepresentable as paths
by construction.

## Network defense (§20–§21)

Per-capsule `NetworkPolicy` (NO_NETWORK default; ALLOWLIST with
suffix-match; FULL_NETWORK flagged high-risk and audited). `check_egress_url()`
blocks metadata endpoints, loopback/link-local/private/reserved literals,
decimal/octal/hex IP tricks (`2130706433`, `0x7f.0.0.1`, `0177.0.0.1`,
`0x7f000001`), non-http(s) schemes, embedded credentials, and suspicious
internal names; DNS names pass only with "resolution-time validation
required", and every allowed URL is additionally checked against the
kernel `NetworkManager` (scopes, budgets, rules). Every request is
attributed (capsule/agent/task/intent/capability/destination/policy) and
recorded allowed/blocked (§22).

## Secrets (§30–§32)

The broker holds values; agents hold opaque binding ids scoped to
agent/capsule/task/capability/destination/time. `use_secret` returns only
fingerprints; `with_resolved` exposes plaintext solely to the provider
callback. Rotation, revocation, per-binding audit, and expiry GC are
implemented; capsule destroy revokes all capsule bindings.

## Risk (§57–§58)

Deterministic weighted sum (authority breadth, irreversibility, external
effects, communication, physical reach, sensors, credentials, network
exposure, data sensitivity, trust, autonomy, lineage) → 0–100 + LOW /
MEDIUM / HIGH / CRITICAL, with named factors. Blast radius is computed
from authority + mounts + policy across 8 scopes and shown by
`capsules.permissions()` / inspector views.

## Quarantine pipeline (§55)

RUNNING → SUSPEND → QUARANTINE → FORENSIC SNAPSHOT → POLICY DECISION →
RECOVER / DESTROY. Evidence is captured before any destructive step;
release requires authority revalidation + manifest verification.

## Anomaly signals (§56)

Rapid action escalation, unexpected capability families, unexpected egress
destinations, tool-call velocity spikes. Strong signals auto-quarantine;
all signals become security events + audit entries.
