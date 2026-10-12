# AetherOS Agent Capsule

Source: `kernel/core/hypervisor/` — `types.py`, `hypervisor.py`, `profiles.py`,
`guards.py`, `filesystem.py`, `secrets.py`, `risk.py`, `isolation.py`.

## Capsule (AgentCapsule)

The controlled execution environment for an agent. Every meaningful
workload executes inside a capsule.

```text
AgentCapsule {
    capsule_id, agent_id, task_id, intent_id
    parent_capsule_id
    identity_key_id, trust_level
    security_profile, capsule_profile
    authority: AuthorityGrant
    capabilities: List[str]          // subset of authority, sealed in manifest
    manifest: CapabilityManifest     // sealed SHA-256
    resource_limits: ResourceBudget
    mounts: List[CapsuleMount]
    network: NetworkPolicy
    memory_policy: MemoryScopeKind
    model_policy: Dict
    tool_policy: Dict
    device_policy: Dict
    secret_policy: Dict
    process_policy: Dict
    environment_policy: Dict
    isolation_level: IsolationLevel
    isolation_provider: str
    lifecycle_state: CapsuleLifecycleState
    checkpoint_id: str | null
    provenance: Dict
    risk: RiskAssessment
    blast_radius: BlastRadius
    autonomy: AutonomyLevel
    node_id: str
    policy_version, policy_hash: str
    contract: AgentCapsuleContract
    created_at, updated_at, expires_at: float
    error: str | null
}
```

## Profiles (§6)

14 standard profiles (defaults, never authorization bypasses):

| Profile | Network | Models | Autonomy | Use |
|---|---|---|---|---|
| `minimal` | NO_NETWORK | local_only | 0 | smallest viable |
| `standard` | ALLOWLIST | cloud+local | 2 | default |
| `developer` | github.com | cloud+local | 2 | coding (git, compiler, terminal) |
| `research` | arxiv, github, api.openai | cloud+local | 2 | browser + evidence |
| `browser` | ALLOWLIST | cloud+local | 2 | isolated browser profile |
| `computer_use` | NO_NETWORK | local_only | 1 | observe-only by default |
| `automation` | ALLOWLIST | cloud+local | 3 | recursion + trigger budgets |
| `swarm` | NO_NETWORK | local_only | 1 | reduced authority, quota |
| `untrusted` | NO_NETWORK | local_only | 0 | max isolation, LEVEL_1 floor |
| `high_security` | ALLOWLIST (empty) | local_only | 1 | approvals for all, immutable audit |
| `physical` | LOCAL_ONLY | local_only | 1 | sensors read, actuators separate |
| `ambient` | NO_NETWORK | local_only | 1 | per-sensor permissions |
| `local_only` | NO_NETWORK | local_only | 1 | privacy |
| `offline` | NO_NETWORK | local_only | 1 | air-gapped |

Profiles are defaults — not authorization bypasses. Anything not in
manifest is unavailable (deny-by-default).

## Lifecycle (§4)

```
REQUESTED → ADMISSION_CHECK → PROVISIONING → INITIALIZING → READY
→ RUNNING ⇄ SUSPENDED → CHECKPOINTING / MIGRATING / RECOVERING
→ COMPLETED → DESTROYED
(+ FAILED / QUARANTINED / TERMINATED)
```

Every transition emits `capsule.lifecycle.transition` + audit.

## Isolation (§7)

```text
LEVEL_0:  Process isolation (scrubbed env, cwd jail, no handle inheritance) — ALWAYS
LEVEL_1:  Sandboxed process (Job Objects on Windows, firejail/container) — detected
LEVEL_2:  Container (docker/podman) — only with reachable daemon
LEVEL_3:  VM isolation — UNAVAILABLE in 1.0
LEVEL_4:  Dedicated host — UNAVAILABLE
```

Provider abstraction (`IsolationProvider.detect()`) reports `SUPPORTED`,
`UNAVAILABLE`, `REQUIRES_CONFIGURATION` with evidence. Profile floors
enforced at provisioning (refuse rather than silently downgrade).

## Filesystem (§17-19)

Per-capsule root: `<base>/<capsule_id>/` (base = `~/.aetheros/capsules`)

```text
/
├── workspace/   READ_WRITE
├── scratch/     TEMPORARY
├── artifacts/   ARTIFACT_MOUNT (append-only via ArtifactManager)
├── cache/       TEMPORARY
├── tmp/         TEMPORARY
├── memory/      READ_WRITE
└── readonly/    READ_ONLY
```

`PathEscapeError` rejects: `../`, absolute host paths, UNC, device paths,
NTFS streams, symlink/junction/reparse escapes (deepest-existing-prefix
resolution). Unknown absolute paths virtualize into capsule-private
storage (contained, never host).

## Network (§20-22)

`NetworkPolicy` modes: `NO_NETWORK`, `LOCAL_ONLY`, `ALLOWLIST`,
`PRIVATE_NETWORK`, `FULL_NETWORK` (high-risk, audited). `check_egress_url()`
blocks metadata endpoints, loopback/private/link-local/reserved literals,
numeric-IP obfuscation, wrong schemes, credentials, internal DNS suffixes.
Hostnames return "resolution-time validation required". Egress attributed
(capsule/agent/task/intent/capability/destination/policy) and logged.

## Secrets (§30-32)

`SecretBroker` — capability-mediated, no plaintext in agent env.
Bindings scoped to agent/capsule/task/capability/destination/time.
`use_secret` returns fingerprint; `with_resolved` passes plaintext only
to provider callback. Rotation, revocation, TTL GC, audit.

## Risk + Blast Radius (§57-58)

`RiskAssessment`: deterministic weighted sum (authority breadth, side
effects, network, data sensitivity, trust, autonomy, lineage) → 0-100,
band LOW/MEDIUM/HIGH/CRITICAL. `BlastRadius` computes from authority +
mounts + policy across 8 scopes. Displayed in inspector views.

## Quarantine + Forensics (§55, §93)

```
RUNNING → SUSPEND → QUARANTINE → FORENSIC SNAPSHOT → POLICY DECISION
→ RECOVER / DESTROY
```

Forensic snapshot captures config, policy, event trace, process tree,
network/filesystem metadata, artifacts, security events — content-minimized.

## Checkpoints (§45-46)

`CapsuleSnapshot` (versioned `AETHEROS_CAPSULE_SNAPSHOT_V1`): metadata,
state, intent, authority, capabilities, manifest hash, policy
version/hash, resource limits, FS metadata, network state, memory refs,
artifacts, tool state, event offset, runtime version, integrity hash.

`snapshot_capsule()` → `CapsuleSnapshot`. `restore_snapshot(hash)` →
in-place (revalidate + capability/manifest reset) or new capsule
(migration target). Tampered snapshot refused (`verify()` fails).

## Replay (§52-54)

Modes: `OBSERVE_ONLY` (default — shows actions, executes 0),
`SIMULATION`/`DRY_RUN` (read-only WOULD_POLICY_CHECK, external
BLOCKED_EXTERNAL), `FULL_EXECUTION` (requires `authorize_full=True` +
fresh human authorization; external effects re-authorized one by one).
External side effects never auto-executed during replay.

## Migration (§47-49)

`pause → checkpoint → verify destination → transfer → restore → verify → resume`
with rollback on failure. Denied if: private data cannot leave node,
physical device local-only, credential cannot transfer, policy differs,
trust insufficient, runtime incompatible. Remote requires node pairing +
mTLS (not configured in 1.0 → REQUIRES_CONFIGURATION).

## Secrets (§30-32)

`SecretBroker` — capability-mediated, no plaintext in agent env.
Bindings scoped to agent/capsule/task/capability/destination/time.
`use_secret` returns fingerprint; `with_resolved` passes plaintext only
to provider callback. Rotation, revocation, TTL GC, audit.

## Termination (§92)

`GRACEFUL` (stop new actions → checkpoint → release → terminate),
`IMMEDIATE`, `FORCED`, `EMERGENCY` (blocks privileged actions
immediately; kernel e-stop independent). Physical capsules command
actuators to safe state (§41).