# AetherOS Update Operations Runbook

## Overview

This runbook covers day-to-day operations for the AetherOS update system, including release management, rollout operations, incident response, and maintenance procedures.

## Release Management

### Creating a Release

```bash
# 1. Ensure you're on the correct branch
git checkout main
git pull origin main

# 2. Run pre-release checks
npm run validate
npm run test:all
npm run security:audit

# 3. Bump version (choose: patch, minor, major, prerelease)
npm run release:bump -- --type patch --channel beta

# 4. Build all platforms
npm run dist:win
npm run dist:mac
npm run dist:linux

# 5. Verify artifacts
npm run release:check

# 6. Create release on update server
aetheros-update-server create-release \
  --version 1.2.3 \
  --channel beta \
  --artifacts ./dist \
  --commit $(git rev-parse HEAD) \
  --release-notes "$(cat RELEASE_NOTES.md)"

# 7. Publish to beta channel
aetheros-update-server publish --release-id <id>
```

### Release Checklist

#### Pre-Release
- [ ] All CI gates passing (tests, typecheck, lint, security)
- [ ] Version bumped correctly (semver)
- [ ] Release notes written
- [ ] Changelog updated
- [ ] Migration scripts tested
- [ ] Performance benchmarks within threshold (Master 71)
- [ ] SBOM generated and verified
- [ ] Provenance attestation verified
- [ ] All platform artifacts built
- [ ] Artifacts signed and notarized
- [ ] Manifest created and signed

#### Release
- [ ] Release created on update server
- [ ] Artifacts uploaded to CDN
- [ ] Manifest published to channel
- [ ] Rollout percentage configured
- [ ] Kill switch verified functional
- [ ] Rollback tested
- [ ] Monitoring alerts active
- [ ] On-call notified

#### Post-Release
- [ ] Rollout metrics monitored
- [ ] Error rates within threshold
- [ ] Rollback rate < 0.1%
- [ ] No P0/P1 issues
- [ ] Documentation updated
- [ ] Release notes published

## Rollout Operations

### Monitoring Rollout

```bash
# Check rollout status
aetheros-update-server rollout-status --channel stable

# View metrics
aetheros-update-server metrics --channel stable --duration 24h

# Advance rollout
aetheros-update-server advance-rollout --release-id abc123 --percentage 25
```

### Rollout Phases (Stable)

| Phase | Percentage | Duration | Action |
|-------|------------|----------|--------|
| Canary | 1% | 24h | Monitor closely |
| Early | 5% | 48h | Check error rates |
| Progressive | 10% | 72h | Verify metrics |
| Broad | 25% | 1 week | Check adoption |
| Majority | 50% | 1 week | Verify stability |
| Full | 100% | 1 week | Complete |

### Advancing Rollout

```bash
# Manual advance (with approval)
aetheros-update-server advance-rollout \
  --release-id abc123 \
  --percentage 25 \
  --approved-by "release-manager"

# Auto-advance (if configured)
aetheros-update-server configure-auto-advance \
  --channel stable \
  --enabled true \
  --criteria '{"errorRate": 0.001, "crashRate": 0.0001}'
```

### Emergency Rollout Override

```bash
# Emergency hotfix with 100% immediate
aetheros-update-server emergency-override \
  --release-id hotfix-123 \
  --percentage 100 \
  --reason "Security hotfix for CVE-2026-XXXX" \
  --authorized-by "security-lead"
```

## Channel Management

### Configuring Channels

```bash
# Configure rollout policy
aetheros-update-server configure-channel \
  --channel beta \
  --percentage 10 \
  --start-date "2026-01-15T10:00:00Z" \
  --cohorts '[{"id": "canary", "platforms": ["win32"], "percentage": 100}]'

# Freeze channel
aetheros-update-server freeze-channel --channel stable --reason "Investigating P0"

# Unfreeze
aetheros-update-server unfreeze-channel --channel stable
```

### Channel Promotion

```bash
# Standard promotion
aetheros-update-server promote \
  --from-channel beta \
  --to-channel stable \
  --release-id abc123 \
  --approvals engineering,security,product

# Emergency promotion
aetheros-update-server promote \
  --from-channel stable \
  --to-channel stable \
  --release-id hotfix-123 \
  --override-rollout 100 \
  --classification security-critical
```

## Incident Response

### Incident Classification

| Severity | Response Time | Escalation |
|----------|---------------|------------|
| P0 (Critical) | 15 min | Page on-call + manager |
| P1 (High) | 1 hour | Page on-call |
| P2 (Medium) | 4 hours | Assign to team |
| P3 (Low) | 24 hours | Schedule fix |

### Common Incidents

#### High Rollback Rate
```bash
# 1. Check rollback metrics
aetheros-update-server metrics --channel stable --metric rollback_rate

# 2. Identify failure pattern
aetheros-update-server rollback-reasons --release-id abc123

# 3. If widespread: activate kill switch
aetheros-update-server kill-switch --release-id abc123 --reason "High rollback rate"

# 4. If isolated: investigate client-specific
aetheros-update-server client-diagnostics --client-id <id>
```

#### Update Server Down
```bash
# 1. Check server health
curl https://updates.aetheros.com/api/v1/health

# 2. If CDN issue: switch to backup CDN
# Update DNS to point to backup

# 3. If origin down: failover to backup region
# Update load balancer

# 4. If signing service down: use backup signing key
# Activate backup HSM
```

#### Malicious Artifact Detected
```bash
# 1. Immediately activate kill switch
aetheros-update-server kill-switch --release-id abc123 --reason "Malicious artifact"

# 2. Revoke release
aetheros-update-server revoke --release-id abc123 --reason "Supply chain compromise"

# 3. Investigate build pipeline
# Check CI logs, artifact hashes, signing logs

# 4. Rotate keys if build compromised
# Rotate manifest signing key from offline root

# 5. Rebuild from clean source
# Full clean build from verified commit

# 6. Publish emergency fix
```

#### Certificate Expiry
```bash
# Check certificate expiry
openssl x509 -in cert.pem -text -noout | grep "Not After"

# Rotate before expiry (30 days notice)
# 1. Generate new CSR
# 2. Submit to CA
# 3. Update HSM
# 4. Test signing
# 5. Update client trust anchors if root changed
```

## Maintenance Procedures

### Daily
- [ ] Check rollout metrics dashboard
- [ ] Review error rates and alerts
- [ ] Verify backup integrity
- [ ] Check certificate expiry (30-day warning)

### Weekly
- [ ] Review rollout metrics trends
- [ ] Check rollback rates and reasons
- [ ] Verify backup/restore procedures
- [ ] Review security advisories
- [ ] Update dependency vulnerabilities

### Monthly
- [ ] Full rollback test (staging)
- [ ] Disaster recovery drill
- [ ] Key rotation review
- [ ] Capacity planning
- [ ] Security audit of update server

### Quarterly
- [ ] Full disaster recovery test
- [ ] Key rotation (manifest signing)
- [ ] Penetration test of update system
- [ ] Review and update runbooks
- [ ] Update documentation

## Backup & Recovery

### Backup Schedule
| Data | Frequency | Retention | Location |
|------|-----------|-----------|----------|
| Update server config | Daily | 30 days | Encrypted S3 |
| Manifests | On publish | 7 years | Immutable storage |
| Artifacts | On publish | 7 years | Immutable storage |
| Signing keys | On rotation | Permanent | Offline HSM |
| Telemetry | Continuous | 90 days | Encrypted DB |

### Recovery Procedures

#### Update Server Recovery
```bash
# 1. Provision new server
# 2. Restore config from backup
# 3. Verify artifact storage access
# 4. Restore signing keys from HSM
# 5. Verify manifest signing
# 4. Update DNS
# 5. Verify health endpoint
```

#### Artifact Storage Recovery
```bash
# 1. Verify immutable storage integrity
# 2. Cross-region replication status
# 3. Rebuild CDN cache
# 5. Verify artifact hashes
```

#### Key Recovery
```bash
# 1. Access offline root CA
# 2. Generate new intermediate
# 3. Sign new intermediate with root
# 3. Deploy to HSM
# 4. Rotate manifests
# 5. Update client trust anchors (if root rotated)
```

## Security Operations

### Key Rotation
```bash
# Manifest signing key (90 days)
# 1. Generate new key pair in HSM
# 2. Sign new intermediate with root
# 3. Update signing service
# 4. Re-sign active manifests
# 5. Update client trust anchors (pinning)

# Platform signing keys (1 year)
# 1. Generate new keys per platform
# 2. Update CI/CD secrets
# 5. Re-sign platform artifacts
# 6. Verify notarization
```

### Vulnerability Response
```bash
# 1. Check affected components
aetheros-update-server scan-vulnerabilities

# 2. Assess impact
# 3. Prepare patch release
# 4. Emergency promotion if critical
# 5. Communicate to users if data at risk
```

## Monitoring & Alerting

### Key Dashboards
- **Rollout Health**: Real-time rollout progress and metrics
- **Error Rates**: Download/install/verification failures
- **Adoption**: Version distribution across users
- **Rollbacks**: Rate, reasons, affected versions
- **Performance**: Download speed, install time, health check latency

### Alert Rules
| Alert | Condition | Severity | Channel |
|-------|-----------|----------|---------|
| Rollback rate spike | >0.1% in 5min | P0 | PagerDuty |
| Install failure rate | >1% in 5min | P1 | PagerDuty |
| Download failure rate | >5% in 5min | P1 | Slack |
| Kill switch activated | Any | P0 | PagerDuty |
| Release revoked | Any | P0 | PagerDuty |
| Certificate expiry | <30 days | P2 | Email |
| Rollout stalled | No advance >24h | P2 | Slack |

### Runbook Links
- [Rollback Runbook](AETHEROS_UPDATE_ROLLBACK.md)
- [Rollout Runbook](AETHEROS_UPDATE_ROLLOUT.md)
- [Security Incident Runbook](AETHEROS_UPDATE_SECURITY.md#incident-response)