# AetherOS Physical Security

## Threat Model (§255)

| Threat | Mitigation | Residual |
|--------|------------|----------|
| Sensor spoofing | Fusion disagreement → STATE_UNCERTAIN | Paraphrased injections → human gate |
| Device spoofing | Pairing + attestation; UNTRUSTED default | Slow-drip poisoning → drift alerts |
| Command injection | HMAC (id/timestamp/nonce/action), 60s skew | Paraphrased injections → review gate |
| Command replay | Nonce cache → REPLAY_REJECTED | Stolen keys within TTL (short TTLs mitigate) |
| Firmware compromise | Version + health tracking | Upstream compromise → attestations |
| Network compromise | mTLS, segmentation, allowlists | Operator responsibility |
| Physical prompt injection | UI/QR/voice as DATA, quarantine | Paraphrased injections → review |
| Data exfiltration | Scrubbing, zones, retention, access | FS-read residual (documented) |
| Unsafe autonomy | Permission ladder, autonomy L0-L5, budgets, e-stop | None accepted silently |
| Rogue device | Pairing + attestation; revoke/lock | Colluding agents → independence check |
| Rogue agent | Remote default-deny; contracts verified | Colluding agents → independence |
| Simulation mismatch | Drift events, TOCTOU version checks | Stale world state |
| Stale world state | Freshness bounds, revalidation | Aggregation leaks → min-N reporting |

## Defense Layers

| Layer | Mechanism |
|-------|-----------|
| Sensor | Fusion disagreement → uncertain; calibration gates |
| Device | Pairing + attestation; UNTRUSTED default |
| Command | HMAC + timestamp + nonce; replay cache |
| Firmware | Version pinning; update hooks need explicit policy |
| Network | mTLS, segmentation, allowlists (operator config) |
| UI/QR/Voice | DATA not AUTHORITY; quarantine on injection |
| Privacy | Scrubbing, zones, retention, access control |
| Remote agent | Default-deny; contracts require identity/trust/provenance |
| Simulation | Mock≠real labeled; sim2real error tracked |
| Emergency | Kill switches fan to M50 global stop |

## Sensor Security

### Fusion Defense
- Disagreement beyond tolerance → `STATE_UNCERTAIN` (never silent pick)
- Quality flags: stale/missing/corrupt/outlier/drifting/inconsistent
- Calibration gates execution

### Data Sanitization
```python
def privacy_scrub(event):
    # Redacts face/person/voice/license_plate
    # Before storage/transmission
```

### Privacy Zones
- Camera masks
- Audio exclusion zones
- Retention limits
- Access control

## Network Security

### SSRF Defense
```python
check_url(url) → DENY for:
- localhost, ::1
- 169.254.169.254 (metadata)
- Private IPs (10.x, 172.16-31, 192.168.x)
- .internal, .local, .corp suffixes
- Decimal/hex IP tricks
- Redirect chains to blocked targets
```

### Egress Budgets
```python
set_egress_budget(scope, max_requests)
# Enforced per scope
```

### Redirect Chain Validation
```python
check_redirect_chain(["https://a.com", "http://10.0.0.1/"])
→ DENY with reason "redirect-to-private"
```

## Command Security

### Authentication
```python
HMAC(identity | action_id | device | capability | nonce | timestamp)
# 60s skew window
# Nonce cache → REPLAY_REJECTED
```

### Replay Protection
- Nonce cache with TTL
- Idempotency keys per action
- Stale command rejection (skew window)

### Authorization
- Capability tokens with audience binding
- Max-use enforcement
- Expiry enforcement

## Remote Agent Security (§226-229)

### Default Policy
```python
remote_policy = "deny"  # No physical control by default
```

### Remote Request
```python
remote_request(agent, action, risk, authorized, evidence)
# Requires: identity + trust + provenance + verification
```

### Result Verification
```python
# Remote results must include:
- device evidence
- sensor evidence  
- timestamp
- execution mode
```

## Device Security

### Pairing & Trust
```
discover → authenticate → verify identity → authorize → register
```
- UNTRUSTED default → OBSERVE_ONLY
- `attest()` for firmware+identity → TRUSTED
- `authorize()` refuses UNTRUSTED
- Revoke → strip permissions
- Human lock / maintenance mode → blocks control

### Credentials
- `CredentialBroker` stores secrets
- Issues short-lived scoped tokens
- Never exposed to LLM/prompts/logs

## Physical Security

### Prompt Injection (§126)
```python
scan_document(text) → {"injection_detected", "quarantine"}
# Treats as DATA, never AUTHORITY
```

### QR/Barcode
```python
decode_qr(payload) → {"data": payload, "trusted": False}
```

### Voice Commands
```python
voice_command(text, authenticated, risk)
# HIGH risk requires auth + confirmation
```

### Physical UI
```python
screen_untrusted_ui_text("Disable safety") 
→ {"blocked": True, "authority": "none"}
```

## Incident Response (§53-55)

### Lifecycle
```
DETECTED → TRIAGED → CONTAINING → CONTAINED
    → INVESTIGATING → RECOVERING → RESOLVED → POSTMORTEM
```

### Containment
| Action | Destructive? | Policy Required |
|--------|-------------|-----------------|
| WARN | No | Never |
| RATE_LIMIT | No | Never |
| PAUSE_AGENT | No | Never |
| REVOKE_CAPABILITY | Yes | Explicit opt-in |
| ISOLATE_TOOL | No | Never |
| BLOCK_NETWORK | Yes | Explicit |
| QUARANTINE_EXTENSION | No | Never |
| STOP_SWARM | No | Never |
| STOP_AUTOMATION | No | Never |
| EMERGENCY_STOP | Yes | Explicit opt-in |

### Auto-containment
```python
# Configurable per incident type
INJECTION_ATTEMPT → WARN + QUARANTINE
CREDENTIAL_MISUSE → REVOKE_CAPABILITY
PHYSICAL_INTRUSION → EMERGENCY_STOP
```

## Audit & Forensics

### Hash-Chained Log
```python
verify_log() → {"ok": bool, "events": n, "message": str}
```

### Tamper Evidence
- Hash chain detects modification
- Cannot prevent admin deletion (documented limit)

### Forensics
- Every action: proposal → decision → authority → execution → result → verification
- Complete provenance chain reconstructable

## Key Management

### Local Custody
- OS keychain / Credential Manager / Secret Service
- AES-256-GCM vault fallback
- Keys never in logs/prompts/audit/renderer

### HSM Path
- PKCS#11 probe at startup
- `LAB_UNAVAILABLE` if no library/token/PIN
- Honest `BLOCKED` — never pretends

### Rotation
- Key expiry tracking
- Auto-rotation for ephemeral
- Manual approval for root keys

## Supply Chain (§126)

### Dependency Verification
```python
validate_package(name, version, expected_hash)
```

### SBOM
- Generated per build
- Signed artifacts

## Certification Claims

| Claim | Status | Evidence |
|---------|--------|----------|
| Sensor spoofing defense | IMPLEMENTED | Fusion conflict tests |
| Device spoofing | IMPLEMENTED | Pairing/attestation tests |
| Command injection | IMPLEMENTED | HMAC + replay tests |
| Firmware compromise | PARTIAL | Version pinning; HSM BLOCKED |
| Network compromise | PARTIAL | mTLS hooks; deployment config |
| Prompt injection | IMPLEMENTED | Scan + quarantine tests |
| Memory poisoning | PARTIAL | Provenance + negative tests |
| Exfiltration | PARTIAL | Scrubbing + audit tests |
| Remote agent compromise | IMPLEMENTED | Default-deny + contract tests |
| Simulation mismatch | IMPLEMENTED | Drift detection tests |
| Stale world state | IMPLEMENTED | Freshness + TOCTOU tests |

## Residual Risks (Accepted)

| Risk | Reason |
|------|--------|
| Admin audit log deletion | Local storage; external SIEM needed |
| DNS rebinding (full) | Requires resolver hardening |
| Insider credential theft | Hardware tokens recommended |
| Supply chain (upstream) | SBOM + signatures mitigate |
| Adaptive prompt injection | Human review gate |
| HSM unavailable | Explicit BLOCKED, not fake |

## Compliance Mapping

| Framework | Controls Mapped |
|-----------|-----------------|
| NIST 800-53 | AC, AU, CM, IA, SC, SI families |
| ISO 27001 | A.8, A.9, A.12, A.13, A.14 |
| SOC 2 | CC6.1, CC6.2, CC6.6, CC7.1 |

## Security Testing

```bash
# Adversarial suite
pytest tests/security/adversarial -v

# Injection tests
pytest tests/security/test_injection.py -v

# Replay/replay
pytest tests/security/test_replay.py -v

# Policy bypass
pytest tests/security/test_policy_bypass.py -v

# Secret exfiltration
pytest tests/security/test_exfiltration.py -v

# Red team suite
pytest tests/security/redteam -v
```

## Incident Response Playbook

1. **Detect** - Alert from monitor/safety/user
2. **Triage** - Severity, scope, evidence
3. **Contain** - Apply containment ladder
4. **Eradicate** - Revoke, patch, rotate
4. **Recover** - Verify, restore, monitor
5. **Learn** - Postmortem → regression test → policy update

## Security Contacts

- Security team: security@aetheros.local
- Emergency: `aetheros trust emergency-stop --layer GLOBAL_KILL`
- Vulnerability disclosure: security@aetheros.local (GPG key on website)