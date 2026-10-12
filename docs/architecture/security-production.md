# AetherOS Security & Production Architecture

This document describes the enterprise security and production-readiness
subsystems shipped in `aetheros_security` and `aetheros_production`. It covers
design intent, module APIs, threat model, and operational guidance. It is the
authoritative reference for the code in these two packages.

## Overview

AetherOS separates infrastructure concerns into two packages:

- **`aetheros_security`** — the security perimeter: encryption, authentication,
  sessions, secrets, sandboxing, policy, privacy, network egress, supply-chain
  verification, threat detection, audit logging, and the orchestrating
  `SecurityManager`.
- **`aetheros_production`** — the operating layer: backup, update system,
  observability (health, diagnostics, crash reporting, metrics, tracing),
  quality gates, packaging, and release management.

Both packages resolve their version from the installed distribution metadata
(`aetheros_security._resolve_version`, `aetheros_production._resolve_version`),
so package versions always match the shipped release. There are no hardcoded
version literals.

---

## Security Package (`aetheros_security`)

### Core principles

1. **Fail closed.** Policy denies by default; sandbox blocks by default; the
   network egress layer blocks by default. Safe defaults are never
   "allow unless told otherwise."
2. **No plaintext secrets at rest.** Secrets are encrypted with a key derived
   from a master key file; `SecretBackend.ENCRYPTED_VAULT` is the production
   backend.
3. **Everything is audited.** Security-relevant events flow through the audit
   logger (`log(event_type, *, severity, user, source, details, ip_address,
   session_id, message)`).
4. **Recoverable.** Every subsystem can be diagnosed and, where possible,
   recovered in place.

### Module reference

| Module | Responsibilities |
| --- | --- |
| `encryption` | AES-GCM authenticated encryption, key rotation, PBKDF2 key derivation, unsalted SHA-256 hashing (deterministic, not for password storage), constant-time HMAC compare. |
| `authentication` | Password auth (Argon2-class hashing via `cryptography`), OAuth provider registration, OTP (single-use), device auth, biometric auth (registered per account). |
| `session` | Signed session tokens with `principal`, `scope`, `timeout_seconds`; create/validate/renew/revoke; tamper and expiry detection. |
| `secrets` | `SecretStore` with get/set/delete/rotate/expiry; value never exposed in metadata; configurable backend (encrypted vault is default). |
| `sandbox` | `SandboxConfig(name, ...)`; import allow/deny lists, filesystem allow/deny, host allow/deny (needs `network_access=True`), path traversal protection; `is_active` property; context-manager and explicit `enter()`/`exit()` modes. |
| `permissions` | Grant-based permission checks, persistent grants in `~/.aetheros/permissions.json` (profile-safe via `get_aetheros_home()`), deny-by-default. |
| `policy` | Named policies loaded from dict or YAML; unknown category rejection; fallback policy; deny-by-default posture. |
| `privacy` | All-off by default; offline blocks outbound collection; consent persistence; PII masking; privacy-mode exports. |
| `network` | Egress control: allow/deny host lists, private-IP blocking, port allowlists, connection and DNS filtering. |
| `supply_chain` | SBOM generation (CycloneDX), SHA-256 artifact verification (`sha256:` prefix), signature verification over digests; unsupported formats raise. |
| `threat` | `record_activity(activity_type=...)` + `analyze_activity()`; signature-based and heuristic threat detection. |
| `audit` | Append-only JSONL audit log, `AuditEventType` (incl. `SECURITY_ALERT`), export to file. |
| `ai_security` / `dlp` / `rate_limit` | LLM-focused security controls, data-loss-prevention, and rate limiting. |

### SecurityManager

`SecurityManager` is the integration facade. It provides:

- `check_permission(...)` / `request_permission(...)`
- `load_policy(name, source)` / `list_policies()`
- `get_audit_log(limit)`
- `run_threat_detection(activity=None)`
- `run_diagnostics()` / `recover(subsystem)` / `get_security_status()`
- `initialize()` — wires default recovery handlers.

Get the singleton with `get_security_manager()`.

---

## Production Package (`aetheros_production`)

### Backup (`backup`)

`BackupManager(home=...)` provides full and incremental backups of the
AetherOS home directory.

- **Includes** (home-relative): `config.yaml`, `.env`, `plugins/`, `skills/`,
  `memory/`, `sessions/`, `cron/`, `state.db`.
- **Encryption**: AES-GCM with AAD `aetheros-backup-v1`; archives are
  encrypted at rest.
- **Safety**: zip-slip protection on extraction; `verify_backup(backup_id)`
  checks archive integrity; `restore_backup(backup_id, *, paths=None,
  verify_first=True)` restores into home.
- **Incremental semantics**: `_files_to_backup` uses strict mtime comparison
  (`>`, not `>=`); `create_backup` anchors `_last_backup_time` to
  `max(newest included file mtime, now)` so same-second re-inclusion cannot
  happen. An incremental backup with no changes returns `status="no_changes"`.
- **API facts**: success returns a dict with `id`, `type`, `size_bytes`,
  `path`, `encrypted` — not a `status` key. `list_backups()` metadata is keyed
  by `backup_id`. `export_backup` / `import_backup` move archives;
  `prune_backups(max_backups=10)` caps retention.
- **Automatic**: a background thread creates scheduled backups.

Get the singleton with `get_backup_manager()`.

### Update System (`update_system`)

`UpdateManager(home=...)` is the over-the-air update path.

- **Release channels**: `stable`, `beta`, `nightly`, persisted in
  `config.yaml` under `updates.channel`; `set_release_channel` / `get_release_channel`.
- **Checking**: `check_for_updates(channel)` fetches a signed manifest over
  HTTPS (lazy `httpx`; any network failure returns `None` — offline-safe);
  `check_and_update` chains check + update.
- **Applying**: `update(target_version, download_url="", package_path=None,
  expected_sha256=None, signature=None)`.
  - A pre-update backup is taken via `BackupManager` before any change.
  - The package is verified: SHA-256 hash must match `expected_sha256`, and the
    signature (if provided) is checked with `verify_signature` (Ed25519 over
    the sha256 hex digest; `DEFAULT_SIGNING_PUBLIC_KEY` is empty until a
    release key is shipped, in which case signature verification is skipped).
  - `.tar.gz`/`.tgz` are extracted with `tarfile.extractall(filter="data")`,
    `.zip` via `zipfile`, and any other file is copied — all staged into
    `<home>/pending_update`, never overwriting live files.
  - After install, `_save_version` updates both the on-disk `version.json` and
    the in-memory `_current_version`.
- **History & rollback**: `add_to_history` / `get_version_history` persist
  to `version_history.json` (newest first, capped at 200 entries);
  `rollback(target_version=None)` restores the newest history entry that
  differs from the current version.
- **Error handling**: `UpdateError` for hash mismatch, missing package,
  and invalid channels.

Get the singleton with `get_update_manager()`.

### Observability (`observability`)

The module combines health, diagnostics, crash reporting, metrics, and
tracing.

- **`HealthChecker`** — component health checks with `HealthStatus` enum
  (`ok`, `degraded`, `failed`, `unknown`); `check_all()` returns full status.
- **`DiagnosticsManager`** — `run_diagnostics()` gathers system/package info;
  `export_diagnostics(report, output_path)` writes JSON.
- **`CrashReporter`** — captures crashes into `crash_*.json` under
  `<home>/crash-reports`, `list_crash_reports()` returns the last 100.
- **`MetricsRegistry`** (added for Phase 10) — thread-safe counters, gauges,
  histograms. API: `increment(name, value=1, labels=None)`, `set_gauge(name,
  value, labels=None)`, `observe(name, value, labels=None)`,
  `snapshot()` (dict with `counters`/`gauges`/`histograms`; histogram has
  `count`/`sum`/`min`/`max`/`avg`), `export_prometheus()` (Prometheus text
  format), `clear()`.
- **`Tracer`** — span-based distributed tracing. `start_span` is a
  contextmanager; `begin_span`/`end_span` are manual. `_new_span` assigns UUID
  trace/span ids, chains `parent_id` from the current span, and caps the span
  buffer at `_max_spans` (1000). `get_traces()` returns trace dicts;
  `export(path)` writes JSON.
- **Singletons**: `get_health_checker()`, `get_diagnostics_manager()`,
  `get_crash_reporter()`, `get_metrics_registry()`, `get_tracer()`.

### Quality gates (`quality`)

`QualityManager` runs self-test suites against the live codebase (no mocks).

- Suites: `smoke`, `regression`, `integration`, `e2e`.
- `run_suite("smoke")` returns `{tests, passed, total}`; `run_test(suite,
  test)` returns a `TestResult`; `run_all_checks()` returns `{pass_rate, suites}`;
  `get_summary()` produces a human-readable report.
- The smoke suite imports the real packages, loads config against a temp
  `AETHEROS_HOME`, discovers plugins via `get_plugin_manager().list_plugins()`,
  and instantiates `agent.memory_manager.MemoryManager`. MCP integration treats
  the optional `mcp` package's absence as a pass. `run_all_checks()` passes
  4/4 across all four suites (pass_rate 1.0).

Get the singleton with `get_quality_manager()`.

### Packaging (`packaging`)

`PackagingManager` builds distributable artifacts.

- `generate_package(format)` supports `homebrew`, `winget`, `chocolatey`,
  `deb`, and related formats. Every format uses the real resolved version —
  no `PLACEHOLDER` tokens. `homebrew`/`winget` artifacts leave
  `sha256 "COMPUTE_AFTER_RELEASE"` for the publisher to fill. `deb` returns a
  graceful `"dpkg-deb not found"` error where the tool is unavailable (e.g.
  Windows).
- `create_portable_bundle(output_dir)` bundles the runtime
  (`sys.prefix`, i.e. the venv) plus the package tree plus a launcher script
  (`.cmd` on Windows, POSIX shell otherwise), archived as zip (Windows) or
  tar.gz. Returns a `PackageResult` with `sha256`.
- `generate_sbom(output_path)` writes a CycloneDX SBOM to
  `dist/sbom.json`, preferring `aetheros_security.supply_chain.generate_sbom`
  and falling back to a self-contained `importlib.metadata` implementation.
- `PackageResult` carries `format`, `path`, `size_bytes`, `success`, `error`,
  `sha256`.

Get the singleton with `get_packaging_manager()`.

### Release management (`release`)

`ReleaseManager` coordinates the release pipeline.

- `get_version_info()` returns the real installed version, channel, edition,
  release date, Python version, and platform.
- `create_release_manifest(output_dir, channel, artifacts=[...])` produces a
  `release.json` with schema_version, version, changelog, known issues,
  breaking changes, migration notes, artifact list, and a SHA-256 `checksums`
  map for every supplied artifact.
- `generate_release_notes()` / `get_changelog()` / `get_migration_guide()` /
  `get_support_matrix()` / `get_license_summary()` provide the standard release
  collateral.

Get the singleton with `get_release_manager()`.

---

## Threat Model

| Asset | Primary control |
| --- | --- |
| Secrets at rest | AES-GCM encrypted vault (`secrets`, `encryption`) |
| Session tokens | Signed + expiry + revocation (`session`) |
| Untrusted code | Import/filesystem/host sandboxing (`sandbox`) |
| Untrusted network | Egress allow/deny + private-IP block (`network`) |
| Tampered artifacts | SHA-256 + Ed25519 signature verification (`supply_chain`, `update_system`) |
| Data loss | Encrypted, verified, prunable backups (`backup`) |
| Malicious activity | Heuristic + signature threat detection (`threat`) |
| Supply chain | CycloneDX SBOM + artifact digests (`packaging`, `supply_chain`) |

## Windows / Cross-Platform Notes

- All text-file I/O uses explicit `encoding="utf-8"` (`PLW1514` is the only
  enforced ruff lint); bare `open()` in text mode defaults to the system
  locale (cp1252 on US Windows) and silently corrupts non-ASCII content.
- Portable bundles and launchers are generated per-platform.
- `tarfile.extractall(filter="data")` rejects path traversal on every OS.

## Testing

The subsystem test suites live in `tests/security/` and `tests/production/`:

- `tests/security/` — encryption, session/auth, policy/privacy/network,
  secrets/sandbox (62 tests).
- `tests/production/` — backup, update system, observability, quality,
  packaging, release (26 tests as of Phase 10).

Both suites run in CI via `.github/workflows/security-testing.yml` on every
PR and weekly against `main`, with `AETHEROS_HOME` pointed at a fresh temp
dir. Combined result: 88 tests, all passing, no warnings.
