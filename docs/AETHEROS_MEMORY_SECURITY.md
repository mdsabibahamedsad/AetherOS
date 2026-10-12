# AetherOS Memory 2.0 — Security & Privacy (Master 41)

## Threat model

Prompt injection, memory poisoning, indirect injection via documents/web,
tool-generated false memories, secret persistence, cross-project/cross-user
leakage, unauthorized access, exfiltration, cache leakage.

## Protections (all enforced, tested in `test_memory2.py`)

- **Provenance trust tiers** (`ProvenanceKind`): web/document-derived content
  can never become `USER_PREFERENCE` without user confirmation; writer
  returns `suggested` instead of storing.
- **Secret refusal**: `contains_secret()` regex gate at record validation
  AND writer time (api keys, bearer tokens, `sk-live-*`, chat tokens,
  private-key blocks, password assignments). `SECRET` privacy class refused
  with pointer to credential store. Memory stores "credential exists for X",
  never the credential.
- **Scope isolation**: project-bound records invisible without matching
  `project_id` (tested both directions).
- **Sensitive inference gate**: `SENSITIVE` inferred memories need
  confirmation (`suggested`, never auto-stored).
- **Tombstone deletion**: `forget` (record/topic/project/all) tombstones
  records, drops project graph nodes, rebuilds the retriever; deleted
  records never returned by any channel.
- **Temporary mode**: `temporary_mode=True` refuses all long-term writes.
- **Procedural memory is advisory**: stored workflows are never executable
  authority (no auto-execute path exists).
- **Remembered authorization ≠ current authorization**: no approval bypass
  reads memory (computer-use integration retrieves context only).
- **IPC**: `memory2.*` methods return plain JSON; no raw renderer/fs/DB
  handles; existing contextIsolation/sandbox posture unchanged.
- **Export**: excludes `SECRET` records and tombstoned records.

## Privacy classes

PUBLIC / INTERNAL / PRIVATE / SENSITIVE / SECRET with writer + quality
enforcement (`classify_privacy`, quality `privacy_violations`/`secret_leaks`).
