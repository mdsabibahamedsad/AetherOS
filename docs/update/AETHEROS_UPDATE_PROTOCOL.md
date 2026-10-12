# AetherOS Update Protocol Specification

## Version
Protocol Version: 1
Document Version: 1.0

## Overview

This document specifies the communication protocol between AetherOS clients and the update server.

## Transport

- **Protocol**: HTTPS (TLS 1.2+)
- **Authentication**: Mutual TLS optional for enterprise; client identifies via User-Agent
- **Compression**: gzip/br for manifest responses
- **Caching**: ETag/If-None-Match for manifest; Cache-Control for artifacts

## Endpoints

### Manifest Retrieval

```
GET /api/v1/updates/{platform}/{architecture}/{channel}
```

#### Path Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| platform | string | `win32`, `darwin`, `linux`, `web`, `ios`, `android` |
| architecture | string | `x64`, `arm64`, `universal` |
| channel | string | `nightly`, `dev`, `alpha`, `beta`, `stable`, `enterprise` |

#### Query Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| current_version | string | Client's current version (semver) |
| build_id | string | Client's build identifier |
| protocol_version | integer | Client's protocol version (default: 1) |

#### Headers
| Header | Value |
|--------|-------|
| Accept | `application/json` |
| User-Agent | `AetherOS-Updater/{version} ({platform}; {arch})` |
| If-None-Match | ETag from previous response (optional) |
| X-AetherOS-Build | Build identifier |

#### Response (200 OK)
```json
{
  "manifest": { ... UpdateManifest ... },
  "etag": "\"abc123...\"",
  "rollout-eligible": true,
  "mandatory": false,
  "retry-after": null
}
```

#### Response (304 Not Modified)
No body. Client continues with current version.

#### Response (404 Not Found)
```json
{
  "error": "NO_UPDATE_AVAILABLE",
  "message": "No update available for this channel/platform/architecture",
  "current_is_latest": true
}
```

#### Response (410 Gone)
```json
{
  "error": "REVOKED_RELEASE",
  "message": "Release has been revoked",
  "revoked_at": "2026-01-15T10:00:00Z"
}
```

#### Response (429 Too Many Requests)
```json
{
  "error": "RATE_LIMITED",
  "message": "Rate limit exceeded",
  "retry_after": 3600
}
```

### Artifact Download

```
GET /api/v1/artifacts/{channel}/{platform}/{architecture}/{version}/{filename}
```

#### Path Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| channel | string | Release channel |
| platform | string | Target platform |
| architecture | string | Target architecture |
| version | string | Release version |
| filename | string | Artifact filename |

#### Query Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| resume | integer | Byte offset for resumable download |

#### Headers
| Header | Value |
|--------|-------|
| Range | `bytes={start}-{end}` (for resumable) |
| Accept | `application/octet-stream` |

#### Response (200 OK / 206 Partial Content)
- Binary artifact stream
- Headers: `Content-Length`, `Content-Type`, `Content-SHA256`, `ETag`, `Accept-Ranges: bytes`

### Release Status

```
GET /api/v1/releases/{releaseId}/status
```

#### Response (200 OK)
```json
{
  "release_id": "abc123...",
  "status": "published",
  "channel": "stable",
  "rollout_percentage": 25,
  "kill_switch": false,
  "published_at": "2026-01-15T10:00:00Z",
  "revoked_at": null,
  "metrics": {
    "downloads": 1234,
    "installs": 1100,
    "failures": 5,
    "rollbacks": 2
  }
}
```

### Channel Configuration

```
GET /api/v1/channels/{channel}/config
```

#### Response (200 OK)
```json
{
  "channel": "stable",
  "rollout_policy": {
    "percentage": 10,
    "cohorts": [],
    "start_date": "2026-01-15T10:00:00Z",
    "end_date": null
  },
  "kill_switch": false,
  "auto_promote": false
}
```

### Health Check

```
GET /api/v1/health
```

#### Response (200 OK)
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-01-15T10:00:00Z",
  "components": {
    "manifest_service": "healthy",
    "artifact_storage": "healthy",
    "signing_service": "healthy"
  }
}
```

## Manifest Structure

See `AETHEROS_UPDATE_ARCHITECTURE.md` for full manifest schema.

### Key Fields
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| product | string | Yes | Always "AetherOS" |
| version | string | Yes | Semantic version |
| channel | string | Yes | Release channel |
| releaseId | string | Yes | Unique release identifier |
| commit | string | Yes | Source commit hash |
| platforms | object | Yes | Platform-specific artifacts |
| minimumVersion | string | Yes | Minimum supported client version |
| artifacts | array | Yes | All artifact metadata |
| releaseNotes | string | Yes | Human-readable changelog |
| security | object | Yes | Security classification |
| rollout | object | Yes | Rollout policy |
| protocolVersion | integer | Yes | Protocol version |
| timestamp | string | Yes | ISO 8601 timestamp |
| signature | string | Yes | Base64-encoded signature |

## Artifact Structure

```json
{
  "platform": "win32",
  "architecture": "x64",
  "version": "1.2.0",
  "buildId": "abc123",
  "sourceCommit": "def456...",
  "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "size": 123456789,
  "signature": "base64...",
  "url": "https://releases.aetheros.com/.../AetherOS-1.2.0-win32-x64.exe",
  "provenance": { ... },
  "packaging": "nsis"
}
```

## Security

### Signature Algorithm
- **Manifest**: RSA-PSS-SHA256 (4096-bit) or Ed25519
- **Artifacts**: Platform-native (Authenticode, codesign, dpkg-sig, RPM)

### Verification Process
1. Verify manifest signature using trusted public key
2. Verify manifest structure and required fields
3. Verify artifact SHA-256 matches manifest
4. Verify artifact signature using platform trust store
5. Verify publisher certificate chain
6. Check certificate expiration
7. Verify rollout eligibility (cohort, percentage, kill switch)
8. Check minimum version compatibility

### Certificate Pinning
Clients should pin the update server's certificate or public key hash.

## Rollout Protocol

### Client-Side Cohort Assignment
```
cohort = first_8_hex_chars(SHA256(device_id + release_id)) % 100
eligible = cohort < rollout_percentage
```

### Server-Side Rollout Control
- Percentage can be adjusted without client update
- Kill switch immediately stops all eligible clients
- Cohort targeting allows platform/architecture/region targeting

## Error Handling

### Client Retry Logic
```
max_retries = 3
base_delay = 2s
max_delay = 60s
jitter = ±25%

for attempt in 1..max_retries:
  try:
    result = request()
    if success: return result
  except TransientError:
    delay = min(base_delay * 2^attempt, max_delay) * (1 + random(-0.25, 0.25))
    sleep(delay)
raise last_error
```

### Transient Errors
- Network timeouts
- 5xx server errors
- 429 rate limiting

### Permanent Errors
- 4xx client errors (except 429)
- Signature/hash verification failures
- Revoked releases

## Version Negotiation

Clients advertise supported protocol versions. Server responds with highest mutually supported version.

### Protocol Version History
| Version | Changes |
|---------|---------|
| 1 | Initial release |

## Deprecation Policy

- Protocol versions supported for minimum 2 years
- 6 months notice before deprecation
- Automatic fallback to previous version during transition

## Rate Limiting

| Tier | Requests/Minute | Burst |
|------|-----------------|-------|
| Anonymous | 10 | 20 |
| Authenticated | 60 | 120 |
| Enterprise | 300 | 600 |

## CDN Integration

Artifacts served via CDN with:
- Immutable URLs (content-addressed)
- `Cache-Control: public, max-age=31536000, immutable`
- `Content-SHA256` header for verification
- Geographic distribution

## Enterprise Extensions

### Private Channels
- Authentication via signed entitlement JWT
- Organization-scoped releases
- Private artifact storage

### Air-Gapped Deployments
- Signed manifest bundles
- Offline verification
- USB/media-based distribution

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-15 | Initial specification |