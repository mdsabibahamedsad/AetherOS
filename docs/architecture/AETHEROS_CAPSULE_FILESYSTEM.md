# AetherOS Capsule Filesystem

Implementation: `kernel/core/hypervisor/filesystem.py` + `guards.py`.

## Layout (§17)

Each capsule gets a private root (`<base>/<capsule_id>/`, base defaults
to `~/.aetheros/capsules`, overridable via `checkpoint_dir`):

```text
<root>/
├── workspace/   READ_WRITE      agent working tree
├── scratch/     TEMPORARY       deleted with the capsule
├── artifacts/   ARTIFACT_MOUNT  append-only via ArtifactManager
├── cache/       TEMPORARY
├── tmp/         TEMPORARY
├── memory/      READ_WRITE      file-backed working notes
└── readonly/    READ_ONLY       reference material
```

The host filesystem is inaccessible unless explicitly mounted: unmounted
absolute paths either resolve into capsule-private storage (container
semantics, e.g. `/etc/passwd` → `<root>/etc/passwd`) or are rejected
(host-absolute forms such as `C:\...`). Anything outside the root raises
`PathEscapeError` with an explicit reason.

## Mounts (§18)

READ_ONLY, READ_WRITE, TEMPORARY, COPY_ON_WRITE (materialize-then-mutate
via `copy_on_write()`), SECRET_MOUNT (rejected as paths — secrets resolve
only through SecretBroker), ARTIFACT_MOUNT (writes blocked; artifacts go
through ArtifactManager), SHARED_MOUNT (explicit cross-capsule sharing).
Every mount records its policy version; `add_mount` validates host
sources; `metadata()` reports bytes/files/mounts for observability and GC.

## Browser/computer surfaces (§36–§37)

Browser profiles live under per-capsule TEMPORARY `browser_profile/`
(cookies, storage, downloads, cache, tabs isolated per capsule).
Computer-use capsules separate OBSERVE from ACT at the capability level
(`computer.observe` vs click/type, the latter never in default profiles).

## Screen data (§38)

`redact_screen_text()` strips `password: ...` assignments, 13–19 digit
card runs, and known key prefixes (`sk-`, `xox*`, `ghp_`) before model
input; screen-capable invocations pass through redaction in `invoke()`.

## Teardown (§117)

`destroy()` exports artifacts only to an explicit destination, then
removes the capsule root; metadata reports what was destroyed. Temp dirs,
browser profiles, and reservations are covered by `gc()`; persistent
artifacts are never deleted implicitly.
