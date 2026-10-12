# AetherOS Security Overview

**Version:** 0.24.0  
**Last Updated:** July 21, 2026

---

## 1. Security Architecture

AetherOS implements a layered security model covering device authentication, data encryption, session management, and audit logging. This document describes the security mechanisms introduced in Phase 13 (Cloud Sync, Multi-Device, Remote Agent Platform) and their integration with the existing security infrastructure.

---

## 2. Device Authentication & Registration

### RSA-4096 Device Identity Keys

Each device generates a persistent RSA-4096 key pair on first initialization:

- **Private key**: Stored in the platform keychain (Windows Credential Manager, macOS Keychain, Linux secret service). Never written to disk as plaintext.
- **Public key**: Registered with the cloud provider and exchanged with peer devices for authentication.

### Registration Flow

```
Device ──► Generate RSA-4096 key pair
  │
  ├─► Store private key in system keychain
  ├─► Send public key + device info to provider
  │       │
  │       ├─► Provider validates request
  │       ├─► Issues device certificate (signed by provider CA)
  │       └─► Returns certificate + device ID
  │
  └─► Device stores certificate
```

### Device Registration API

```python
# Register a new device
device_id = security.register_device(
    device_name="My Laptop",
    device_type="desktop",
    public_key=public_key_pem
)

# List registered devices
devices = security.list_devices()

# Revoke device access
security.revoke_device(device_id="dev-abc123")
```

---

## 3. Session Management with Token Rotation

### JWT Sessions

All authenticated sessions use JSON Web Tokens with strict expiration:

```json
{
  "jti": "token-uuid",
  "sub": "device-id",
  "iss": "aetheros-sync",
  "iat": 1712345678,
  "exp": 1712349278,
  "scopes": ["sync:read", "sync:write", "remote:control"],
  "device_id": "dev-abc123"
}
```

### Token Lifecycle

```
Issue ──► Active (TTL: 1h) ──► Refresh (55min) ──► New token
  │                                                    │
  └──► Expired (1h) ──► Re-authenticate ◄──────────────┘
```

- **Issue**: On successful device authentication.
- **Refresh**: Automatic background refresh at 55 minutes.
- **Revoke**: On device disconnect or security event.
- **Blacklist**: Revoked tokens added to blacklist until natural expiry.

### Token Security

- Signed with HS256 (provider-side) or Ed25519 (self-hosted).
- Token blacklist stored in-memory with TTL equal to remaining token lifetime.
- Refresh tokens are one-time-use; each refresh invalidates the previous token.

---

## 4. End-to-End Encryption for Secrets

All credentials, API keys, and sensitive configuration data are end-to-end encrypted using the device's RSA-4096 key pair.

### Secret Encryption Flow

```python
# Encrypt a secret for a specific device
encrypted_secret = security.e2ee_encrypt(
    plaintext="sk-abc123...",
    recipient_public_key=peer_public_key,
    sender_private_key=my_private_key
)

# Decrypt on receiving device
plaintext = security.e2ee_decrypt(
    ciphertext=encrypted_secret,
    recipient_private_key=my_private_key,
    sender_public_key=peer_public_key
)
```

### Key Exchange

- Diffie-Hellman-style ECDH key agreement over the RSA key pairs.
- Shared secret derived using HKDF for each encryption session.
- Forward secrecy: compromise of current keys does not expose past sessions.

---

## 5. AES-256-GCM Sync Encryption

All sync payloads are encrypted using AES-256 in Galois/Counter Mode:

```
plaintext
  │
  ├─► Generate 96-bit random nonce
  ├─► Encrypt with AES-256-GCM(key, nonce)
  ├─► Append 128-bit authentication tag
  │
  ▼
ciphertext + nonce + auth_tag
```

- **Key**: 256-bit, derived from user sync passphrase via PBKDF2.
- **Nonce**: Unique per encryption operation; transmitted in plaintext.
- **Auth tag**: Verified on decryption; ensures integrity + authenticity.
- **AAD** (Additional Authenticated Data): device_id + scope + version — prevents ciphertext reuse across contexts.

### Encryption Key Derivation

```
PBKDF2(
    password = user_passphrase,
    salt = 16_bytes_random,
    iterations = 600000,
    key_length = 32,
    hash = SHA-256
) → 256-bit key
```

---

## 6. RSA-4096 Device Identity Keys

Managed through the operating system's secure keychain:

| Platform | Storage | API |
|----------|---------|-----|
| Windows | Credential Manager | `win32cred` |
| macOS | Keychain | `Security.framework` |
| Linux | Secret Service (D-Bus) | `secretstorage` |
| Fallback | Encrypted file | `~/.aetheros/keys/device.key` (AES-256 encrypted) |

### Key Operations

```python
# Generate new key pair
key_pair = security.generate_device_key()

# Sign a payload
signature = security.sign(payload, private_key=key_pair.private_key)

# Verify a signature
is_valid = security.verify(payload, signature, public_key=sender_public_key)

# Export public key (for registration)
public_key_pem = key_pair.public_key.export_pem()
```

---

## 7. PBKDF2 Key Derivation

Used to derive encryption keys from user-supplied passphrases:

```python
key = security.derive_key(
    passphrase="user-sync-passphrase",
    salt=os.urandom(16),
    iterations=600000,
    key_length=32,
    algorithm="pbkdf2-hmac-sha256"
)
```

- **Iterations**: 600,000 by default (auto-adjusted: target < 1s on device hardware).
- **Salt**: 16 bytes, randomly generated per derivation.
- **Output**: 256-bit key suitable for AES-256-GCM.

---

## 8. Digital Signatures for Payload Verification

Every sync payload is digitally signed to ensure non-repudiation:

### Signing

```python
# Create signature
payload_bytes = json.dumps(payload).encode()
payload_hash = hashlib.sha256(payload_bytes).digest()
signature = rsa.sign(payload_hash, private_key, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32), hashes.SHA256())
```

### Verification

```python
# Verify signature
payload_hash = hashlib.sha256(payload_bytes).digest()
try:
    rsa.verify(payload_hash, signature, public_key,
               padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32),
               hashes.SHA256())
    return True
except InvalidSignature:
    return False
```

---

## 9. Audit Logging for All Security Events

### Event Categories

| Category | Events |
|----------|--------|
| Authentication | `auth.success`, `auth.failure`, `auth.token_issued`, `auth.token_refreshed`, `auth.token_revoked` |
| Device Management | `device.registered`, `device.revoked`, `device.key_rotated` |
| Sync | `sync.started`, `sync.completed`, `sync.failed`, `sync.conflict_detected` |
| Remote Access | `remote.connected`, `remote.disconnected`, `remote.command_executed` |
| Encryption | `encryption.key_exchange`, `encryption.key_rotation` |

### Audit Log Entry

```json
{
  "event_id": "evt-20260721-abc123",
  "timestamp": "2026-07-21T10:30:00.123Z",
  "category": "authentication",
  "event": "auth.success",
  "device_id": "dev-abc123",
  "source_ip": "192.168.1.100",
  "details": {
    "method": "mTLS + token",
    "session_id": "sess-xyz"
  },
  "severity": "info"
}
```

---

## 10. Permission Validation per Device

Each device has a permission set stored in the device registry:

```json
{
  "device_id": "dev-abc123",
  "permissions": {
    "sync": {
      "scopes": ["settings", "agents", "configs"],
      "max_bytes_per_sync": 10485760,
      "allowed_providers": ["local", "custom"]
    },
    "remote": {
      "max_connections": 3,
      "allowed_commands": ["start", "stop", "status"],
      "workspace_access": ["files", "knowledge"]
    },
    "admin": false
  }
}
```

### Permission Check Flow

```
Request → Extract device_id from token
  → Load device permissions from registry
  → Validate request against permission set
  → Allow or Deny with audit log entry
```

---

## 11. Rate Limiting for Remote Connections

| Scope | Limit | Window |
|-------|-------|--------|
| Authentication attempts | 5 | 60 seconds |
| Sync requests | 60 | 60 seconds |
| Remote commands | 30 | 60 seconds |
| File operations | 20 | 60 seconds |
| Global (per device) | 100 | 60 seconds |

Rate limit headers returned on 429 responses:

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1712349330
Retry-After: 30
```

---

## 12. Secure Keychain Integration

All secrets and keys are stored in the OS keychain rather than in configuration files:

```python
# Store a secret
security.keychain.set("sync_passphrase", value, service="aetheros-sync")

# Retrieve a secret
passphrase = security.keychain.get("sync_passphrase", service="aetheros-sync")

# Delete a secret
security.keychain.delete("sync_passphrase", service="aetheros-sync")
```

### Keychain Entries

| Entry | Service | Description |
|-------|---------|-------------|
| `device_private_key` | `aetheros-device` | RSA-4096 private key |
| `sync_passphrase` | `aetheros-sync` | Sync encryption passphrase |
| `provider_token` | `aetheros-sync` | Cloud provider auth token |
| `remote_node_tokens` | `aetheros-remote` | Per-node authentication tokens |

---

## 13. Never Log Credentials

The following rules are enforced across all sync and remote agent code:

1. **Never log:**
   - API keys, tokens, passphrases
   - Private keys (RSA, encryption)
   - Session tokens
   - Plaintext payload content
   - Device secrets

2. **Log only:**
   - Event type and category
   - Device IDs (not device secrets)
   - Timestamps
   - Success/failure status
   - Non-sensitive metadata (file sizes, sync counts)

3. **Redaction patterns applied to all log output:**
   - `sk-*` → `sk-***REDACTED***`
   - `Bearer *` → `Bearer ***REDACTED***`
   - JWT tokens → `***REDACTED***`

---

## 14. Device Revocation

### Revocation Flow

```
Admin triggers revoke → Audit log entry
  → Token blacklist updated
  → Provider notified
  → Peer devices notified
  → Device certificate added to CRL
  → Connected sessions terminated
```

### Revocation Effects

| Service | Effect |
|---------|--------|
| Sync | Device can no longer sync. Existing sync data preserved. |
| Remote | Active connections terminated immediately. |
| Agent | Remote agents stop accepting commands from device. |
| Key exchange | Device removed from key exchange participants. |

### Re-registration

A revoked device must go through the full registration flow again, generating new keys and receiving a new certificate.
