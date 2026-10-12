# Authentication

Implemented mechanism: **API keys** (`aetheros_platform/auth.py`).

- Creation: `APIKeyManager.create(name, scopes, owner)` returns a
  display-once secret (`aek_...`, shown once with an explicit warning).
- Storage: scrypt (`n=2^14`) + per-key salt in SQLite; plaintext is
  never listed (`key_hash`/`api_key` excluded from `list()` — tested).
- Transport: `X-API-Key` header or `Authorization: Bearer`.
- Lifecycle: expiry (`expiresInDays` 1–365), `last_used_at` tracking,
  `revoke()`, `rotate()` — revoked/expired keys → 401
  `AUTHENTICATION_REQUIRED` (tested: `test_revoked_and_expired_rejected`).
- Every credential carries scope, owner, creation/expiry, status.

Explicitly NOT implemented: OAuth 2.x, OIDC, mTLS, service/device
identities (`auth.py` documents this; no flows are faked). Local
development uses keys issued by `python -m aetheros_platform.cli auth
key-create`. SDKs verify TLS by default (`httpx.Client(verify=True)`,
fetch platform default) and never log secrets.
