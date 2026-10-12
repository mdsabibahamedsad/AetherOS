# AetherOS Sync Architecture

**Version:** 0.23.0  
**Last Updated:** July 21, 2026

---

## 1. Overview

The AetherOS Sync System provides **offline-first**, **end-to-end encrypted** synchronization across multiple devices. It enables seamless transitions between offline and online states, conflict resolution, version history, and collaborative multi-device workflows.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SYNC SYSTEM OVERVIEW                         │
│                                                                     │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐        │
│  │ Device A  │   │ Device B  │   │ Device C  │   │   ...    │        │
│  │ (Desktop) │   │  (Laptop) │   │  (Mobile) │   │ (n-Devs) │        │
│  └─────┬─────┘   └─────┬─────┘   └─────┬─────┘   └─────┬─────┘        │
│        │               │               │               │            │
│  ┌─────┴───────────────┴───────────────┴───────────────┴────────┐  │
│  │                    SYNC ENGINE                                │  │
│  │  ┌───────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │  │
│  │  │  Conflict │ │  Delta   │ │  Version │ │  Background  │  │  │
│  │  │ Resolver  │ │  Engine  │ │  History │ │  Sync Queue  │  │  │
│  │  └───────────┘ └──────────┘ └──────────┘ └──────────────┘  │  │
│  └───────────────────────────┬──────────────────────────────────┘  │
│                              │                                      │
│  ┌───────────────────────────▼──────────────────────────────────┐  │
│  │                  CLOUD PROVIDER ABSTRACTION                   │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐                │  │
│  │  │   Local    │ │   Custom   │ │   (Future) │                │  │
│  │  │  Provider  │ │  Provider  │ │  Providers │                │  │
│  │  └────────────┘ └────────────┘ └────────────┘                │  │
│  └───────────────────────────┬──────────────────────────────────┘  │
│                              │                                      │
│  ┌───────────────────────────▼──────────────────────────────────┐  │
│  │                   ENCRYPTION LAYER                            │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐  │  │
│  │  │ AES-256- │ │ RSA-4096 │ │ PBKDF2  │ │  Digital       │  │  │
│  │  │   GCM    │ │ Dev Keys │ │ Key Der.│ │  Signatures    │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Design Principles

- **Offline-first**: Every device stores a full local copy. Writes succeed immediately offline and sync when connectivity returns.
- **End-to-end encrypted (E2EE)**: Data is encrypted on the sending device and decrypted only on authorized receiving devices.
- **Conflict-free**: Last-writer-wins, manual merge, and custom resolution strategies.
- **Incremental**: Only changed data is transmitted via delta updates.
- **Pluggable providers**: Abstract cloud backend supports local filesystem, custom servers, and future cloud services.

---

## 2. Offline-First Architecture

### Local-First Storage Model

Each device maintains a complete local data store. All operations — reads, writes, queries — are served from the local store without requiring network connectivity.

```
┌─────────────────────────────────────────────────────┐
│                LOCAL DATA STORE                       │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────────┐ │
│  │ SQLite  │ │  YAML   │ │  JSON   │ │  File     │ │
│  │  (DB)   │ │ (Config)│ │ (State) │ │  System   │ │
│  └────┬────┘ └────┬────┘ └────┬────┘ └─────┬─────┘ │
│       │           │           │              │       │
│  ┌────┴───────────┴───────────┴──────────────┴────┐ │
│  │           Sync Queue (Outbox Pattern)            │ │
│  │  ┌──────────────────────────────────────────┐  │ │
│  │  │  Pending Changes │ Retry Queue │ Conflict│  │ │
│  │  └──────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### Sync Queue (Outbox Pattern)

All mutations are written to the local store immediately and enqueued in the outbox. The background sync processor drains the outbox when connectivity is available.

```
Offline:
  Write → Local Store (immediate) → Outbox Queue (pending)

Online:
  Outbox Queue → Delta Engine → Compress → Encrypt → Cloud Provider → Ack
```

---

## 3. Sync Engine Design

The sync engine (`sync_engine.py`) is the core orchestrator that coordinates all synchronization activities.

### Core Components

| Component | Responsibility |
|-----------|---------------|
| **SyncEngine** | Top-level orchestrator: manages sessions, coordinates sync passes |
| **DeltaEngine** | Computes minimal change sets between local and remote states |
| **ConflictResolver** | Applies configured conflict strategy per scope |
| **VersionHistory** | Maintains immutable version chain for restore capability |
| **BackgroundSync** | Runs periodic sync passes with connectivity awareness |
| **RetryQueue** | Manages exponential-backoff retries for failed sync operations |

### Sync Session Lifecycle

```
START_SYNC
  │
  ├─► Lock acquired (per-scope mutex)
  ├─► Compute local delta since last sync cursor
  ├─► Fetch remote delta from provider
  ├─► Merge: apply remote deltas locally (with conflict resolution)
  ├─► Push: apply local deltas to remote (with conflict resolution)
  ├─► Update sync cursor / version history
  └─► Release lock → COMPLETE (or CONFLICT / ERROR)
```

### Sync Scope Management

Each sync scope operates independently with its own lock, cursor, version chain, and sync frequency.

| Scope | Description | Sync Cadence |
|-------|-------------|-------------|
| `settings` | User preferences and config | On change |
| `agents` | Agent definitions and configs | On change |
| `configs` | System configuration | On change |
| `workflows` | Automation workflows | On change |
| `automations` | Automation rules | On change |
| `provider_configs` | AI provider credentials (encrypted) | On change |
| `model_preferences` | Model favorites, pins, routing | On change |
| `knowledge_metadata` | Knowledge base metadata (not content) | Periodic |
| `memory` | Memory index data | Periodic |
| `chat_history` | Conversation metadata | Periodic |
| `plugins` | Plugin configs and state | On change |
| `mcp_configs` | MCP server configs | On change |
| `workspace_metadata` | Workspace settings | On change |
| `themes` | UI theme and skin configs | On change |
| `shortcuts` | Custom keyboard shortcuts | On change |
| `notifications` | Notification preferences | On change |

### Sync Cursor

Each scope tracks a monotonic cursor (timestamp + sequence number) to determine the set of changes since the last successful sync.

```json
{
  "scope": "agents",
  "device_id": "dev-abc123",
  "last_cursor": 1712345678,
  "last_sync_at": "2026-07-21T10:30:00Z",
  "checksum": "sha256:abc123..."
}
```

---

## 4. Incremental Sync & Delta Updates

The delta engine computes minimal change sets using version vectors and content-addressable storage.

### Change Detection

1. Each data entity has a `version` (monotonic counter) and `checksum` (SHA-256 of serialized content).
2. The delta engine compares local vs remote version vectors to identify:
   - **New entities** (exist on one side only)
   - **Updated entities** (version differs)
   - **Deleted entities** (tombstone marker)
3. For each changed entity, only the serialized payload and metadata are transmitted.

### Delta Format

```json
{
  "sync_id": "sync-20260721-abc123",
  "device_id": "dev-abc123",
  "scope": "agents",
  "base_cursor": 1712345678,
  "changes": [
    {
      "op": "upsert",
      "id": "agent-001",
      "version": 42,
      "checksum": "sha256:def456...",
      "data": "<encrypted-payload>"
    },
    {
      "op": "delete",
      "id": "agent-002",
      "version": 17
    }
  ],
  "tombstones": ["agent-003", "agent-004"]
}
```

### Compression

Deltas are compressed using zstd (level 3) before transmission. Large payloads (>1MB) are chunked automatically.

---

## 5. Conflict Resolution Strategies

Conflicts occur when the same entity is modified on two devices between sync passes. The system supports five strategies, configurable per scope.

| Strategy | Behavior | Use Case |
|----------|----------|----------|
| `latest` | Last-writer-wins (default). Timestamp comparison determines winner. | Chat history, logs |
| `manual` | Conflict is flagged for user resolution. Both versions stored. | Settings, configs |
| `keep-local` | Local version always wins. Remote changes discarded. | Provider configs |
| `keep-remote` | Remote version always wins. Local changes overwritten. | Shared workflows |
| `merge` | Field-level merge where possible; conflicts escalated to manual. | Agent configs, themes |

### Conflict Record

```json
{
  "conflict_id": "conflict-20260721-xyz789",
  "scope": "agents",
  "entity_id": "agent-001",
  "device_a": { "device_id": "dev-abc123", "version": 42, "updated_at": "..." },
  "device_b": { "device_id": "dev-def456", "version": 43, "updated_at": "..." },
  "resolution": "pending",
  "resolved_at": null,
  "resolved_by": null
}
```

---

## 6. Version History & Restore

Every sync pass creates an immutable version snapshot per scope. Users can browse history and restore to any previous version.

### Version Chain

```
v1 ──► v2 ──► v3 ──► v4 ──► ... (linear per scope)
         ↖ conflict branch ↙
           v2b ──► v3b
```

- Each version stores: snapshot checksum, timestamp, device ID, change summary.
- Retention policy: keep last 100 versions per scope (configurable).
- Restore: select version → engine replays reverse deltas or applies full snapshot.

### Restore API

```python
# Restore scope "agents" to version 42
sync_engine.restore(scope="agents", version=42)

# Dry-run restore preview
changes = sync_engine.preview_restore(scope="agents", version=42)
```

---

## 7. Cloud Provider Abstraction

The `CloudProviderBase` abstract class defines the interface for all cloud backends.

### Interface

```python
class CloudProviderBase(ABC):
    @abstractmethod
    async def initialize(self, config: dict) -> bool: ...

    @abstractmethod
    async def get_delta(self, scope: str, cursor: int) -> Delta: ...

    @abstractmethod
    async def apply_delta(self, scope: str, delta: Delta) -> int: ...

    @abstractmethod
    async def get_version_history(self, scope: str, limit: int) -> list: ...

    @abstractmethod
    async def restore_version(self, scope: str, version: int) -> bool: ...

    @abstractmethod
    async def health_check(self) -> HealthStatus: ...

    @abstractmethod
    async def get_device_registry(self) -> list[DeviceInfo]: ...

    @abstractmethod
    async def register_device(self, device_info: DeviceInfo) -> bool: ...
```

### Built-In Providers

#### Local Provider

- Stores sync data in the local filesystem (`~/.aetheros/sync/`).
- Primarily for single-device operation or as an intermediary cache.
- No network required.
- Supports all sync and conflict resolution features.

#### Custom Provider

- Generic HTTP/HTTPS provider for self-hosted sync servers.
- Endpoints configurable via provider config.
- Supports authentication (bearer token, basic auth, mutual TLS).
- Example: `aetheros/sync-server` Docker image.

### Built-In Providers

| Provider | Type | Description |
|----------|------|-------------|
| Local | Filesystem | Local-only sync store |
| Custom | HTTP/S | Self-hosted or third-party sync server |

---

## 8. Encryption Layer

The encryption layer (`sync_crypto.py`) provides end-to-end encryption for all sync data.

### AES-256-GCM (Data Encryption)

All sync payloads are encrypted with AES-256-GCM (Galois/Counter Mode), providing both confidentiality and authenticated integrity.

```
plaintext + AES-256-GCM(key, nonce) → ciphertext + auth_tag
  ↓
ciphertext + auth_tag + nonce → transmitted payload
  ↓
ciphertext + auth_tag + nonce + AES-256-GCM(key, nonce) → plaintext
```

- Key: 256-bit derived from user passphrase via PBKDF2.
- Nonce: 96-bit random per encryption operation.
- Auth tag: 128-bit, verified on decryption.
- Additional Authenticated Data (AAD): device_id + scope + version.

### End-to-End Encryption (E2EE)

Data encrypted on the source device can only be decrypted by authorized devices.

```
Device A encrypts → Ciphertext transmitted via provider → Device B decrypts
                                 │
                    Provider cannot decrypt
                    (only stores opaque ciphertext)
```

### RSA-4096 Device Identity Keys

Each device generates an RSA-4096 key pair on first registration:

- **Private key**: stored in device keychain, never transmitted.
- **Public key**: registered with the sync provider, used for device authentication and encryption key exchange.

### PBKDF2 Key Derivation

User sync passphrases are derived into encryption keys using PBKDF2:

```
PBKDF2(password, salt, iterations=600000, key_length=32, hash=SHA-256)
```

- Salt: 16 bytes random, stored alongside encrypted data.
- Iterations: 600,000 (configurable, auto-adjusted for hardware).

### Digital Signatures

All sync payloads are signed with the device's RSA-4096 private key:

```
signature = RSA_SIGN(SHA-256(payload), device_private_key)
```

Receiving devices verify:
```
RSA_VERIFY(payload, signature, sender_public_key)
```

This ensures non-repudiation and payload integrity across devices.

---

## 9. Performance

### Compression

| Algorithm | Level | Use Case |
|-----------|-------|----------|
| zstd | 3 | Default payload compression |
| zstd | 9 | Large batch syncs (>10MB) |
| None | — | Already-compressed content (images, archives) |

### Lazy Loading

- Sync metadata (version vectors, change lists) fetched first.
- Full payloads fetched on demand when a device needs the data.
- Reduces sync time for large scopes (e.g., chat history).

### Background Sync

- Runs on configurable intervals (default: 5 minutes).
- Respects system power state (pauses on battery ≤20%).
- Connectivity-aware: polls for network availability before attempting.
- Throttles to avoid CPU contention during active user sessions.

### Retry Queue

| Attempt | Wait Time |
|---------|-----------|
| 1 | 10s |
| 2 | 30s |
| 3 | 60s |
| 4 | 120s |
| 5 | 300s |
| 6+ | 600s (cap) |

### Connection Recovery

- Automatic reconnection with exponential backoff.
- Connection health check with 30-second heartbeat.
- Partial sync recovery: resumes from last acknowledged change, not full replay.

---

## 10. Security

### Device Authentication

Each device authenticates using its RSA-4096 key pair:

1. Device presents device_id + signed challenge.
2. Provider verifies signature against registered public key.
3. Session token issued (1-hour TTL).

### Session Management

- Tokens: JWT with device_id, scopes, expiry.
- Rotation: tokens rotated every hour; old tokens invalidated.
- Refresh: automatic background token refresh before expiry.

### Token Rotation Schedule

```
Issue Token (TTL: 1h) ──► Auto-Refresh (55min) ──► New Token (TTL: 1h)
                              │
                              └─► If refresh fails → Re-authenticate
```

### Audit Logs

All security events are logged to the sync audit trail:

| Event | Description |
|-------|-------------|
| `device.register` | New device registered |
| `device.revoke` | Device revoked from account |
| `sync.start` | Sync session initiated |
| `sync.complete` | Sync session completed |
| `sync.conflict` | Conflict detected |
| `sync.conflict.resolved` | Conflict resolved |
| `auth.token.issue` | Session token issued |
| `auth.token.refresh` | Session token refreshed |
| `auth.token.revoke` | Session token revoked |
| `auth.failure` | Authentication failure |
| `encryption.key_exchange` | E2EE key exchange completed |

---

## 11. Error Handling

### Error Categories

| Category | Retry | Recovery |
|----------|-------|----------|
| Network timeout | Yes (3 attempts) | Queue for retry |
| Authentication failure | No | Re-authenticate device |
| Conflict | Depends on strategy | Auto or manual resolve |
| Provider unavailable | Yes (exponential backoff) | Switch to offline mode |
| Payload corrupt | No | Re-fetch from provider |
| Encryption mismatch | No | Re-key exchange |

### Error Notifications

- UI notifications for unresolved conflicts.
- Audit log entries for all sync failures.
- Health check endpoint for monitoring sync status.

---

## 12. Configuration

### Sync Config (`config.yaml`)

```yaml
sync:
  enabled: true
  provider: local  # "local" | "custom"
  interval_seconds: 300
  retry_attempts: 5
  compression: zstd
  compression_level: 3
  lazy_loading: true
  background_sync: true

  scopes:
    settings: { strategy: latest, enabled: true }
    agents: { strategy: merge, enabled: true }
    configs: { strategy: manual, enabled: true }
    workflows: { strategy: keep-remote, enabled: true }
    automations: { strategy: latest, enabled: true }
    provider_configs: { strategy: keep-local, enabled: true }
    model_preferences: { strategy: latest, enabled: true }
    knowledge_metadata: { strategy: latest, enabled: true }
    memory: { strategy: latest, enabled: true }
    chat_history: { strategy: latest, enabled: false }
    plugins: { strategy: manual, enabled: true }
    mcp_configs: { strategy: manual, enabled: true }
    workspace_metadata: { strategy: keep-local, enabled: true }
    themes: { strategy: latest, enabled: true }
    shortcuts: { strategy: latest, enabled: true }
    notifications: { strategy: latest, enabled: true }

  encryption:
    enabled: true
    algorithm: aes-256-gcm
    key_derivation: pbkdf2
    pbkdf2_iterations: 600000
    e2ee: true
    signing_algorithm: rsa-4096

  version_history:
    enabled: true
    max_versions_per_scope: 100
    retention_days: 90
```
