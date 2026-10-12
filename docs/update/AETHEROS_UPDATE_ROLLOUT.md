# AetherOS Update Rollout Strategy

## Overview

This document describes the rollout strategy for AetherOS updates, including gradual rollout, cohort targeting, promotion between channels, and emergency controls.

## Release Channels

### Channel Hierarchy

```
nightly → dev → alpha → beta → stable → enterprise
```

Each channel is independent with its own:
- Update feed URL
- Rollout policy
- Release metadata
- Approval requirements

### Channel Characteristics

| Channel | Audience | Rollout | Approvals | Use Case |
|---------|----------|---------|-----------|----------|
| nightly | Internal developers | 100% immediate | 0 | Latest development |
| dev | Internal team | 100% immediate | 1 | Integration testing |
| alpha | Early adopters | 25% gradual | 1 | Feature preview |
| beta | Power users | 10% gradual | 2 | Pre-release validation |
| stable | All users | 5% → 100% gradual | 3 | Production releases |
| enterprise | Enterprise customers | 100% controlled | 1 | Long-term support |

## Rollout Policies

### Percentage-Based Rollout

```json
{
  "percentage": 10,
  "cohorts": [],
  "startDate": "2026-01-15T10:00:00Z",
  "endDate": "2026-01-22T10:00:00Z"
}
```

- **Percentage**: 0-100, controls what fraction of eligible clients receive the update
- **Start Date**: When rollout begins
- **End Date**: Optional, when rollout reaches 100%
- **Cohorts**: Optional targeting rules

### Gradual Rollout Schedule (Stable Channel)

| Phase | Percentage | Duration | Criteria to Advance |
|-------|------------|----------|---------------------|
| Canary | 1% | 24 hours | Zero critical failures |
| Early | 5% | 48 hours | <0.1% failure rate |
| Progressive | 10% | 72 hours | <0.05% failure rate |
| Broad | 25% | 1 week | No regressions |
| Majority | 50% | 1 week | Stable metrics |
| Full | 100% | 1 week | All clear |

### Automatic Advancement
- Health metrics monitored continuously
- Auto-advance if criteria met
- Manual override always available
- Rollback on any P0 regression

## Cohort Targeting

### Cohort Definition
```json
{
  "id": "windows-x64-canary",
  "platforms": ["win32"],
  "architectures": ["x64"],
  "regions": ["US", "CA"],
  "channels": ["beta"],
  "percentage": 100
}
```

### Targeting Dimensions
| Dimension | Values | Use Case |
|-----------|--------|----------|
| Platform | win32, darwin, linux, web, ios, android | Platform-specific fixes |
| Architecture | x64, arm64, universal | Architecture-specific fixes |
| Region | ISO 3166-1 alpha-2 | Regional rollout, compliance |
| Channel | nightly, dev, alpha, beta, stable, enterprise | Channel-specific |
| App Version | Semver range | Migration from specific versions |
| Device Type | desktop, mobile, server | Form factor specific |
| Opt-in Group | String | User opt-in programs |

### Cohort Evaluation
- Client evaluates all applicable cohorts
- Most specific matching cohort wins
- Percentage applied within cohort
- Deterministic assignment via hash

## Promotion Workflow

### Automated Promotion Criteria

| From → To | Requirements |
|-----------|--------------|
| nightly → dev | All CI passing, no P0 bugs |
| dev → alpha | 48h stable, telemetry green |
| alpha → beta | 1 week stable, <0.1% crash rate |
| beta → stable | 2 weeks stable, zero P0/P1, security audit |
| stable → enterprise | 1 month stable, LTS branch cut |

### Manual Promotion Gates
1. **Engineering Approval**: Tech lead sign-off
2. **Security Review**: Security team approval for stable
3. **Product Approval**: PM sign-off for user-facing changes
4. **Release Manager**: Final coordination and scheduling

### Promotion Process
```bash
# Automated promotion (CI/CD)
promote-release \
  --from-channel beta \
  --to-channel stable \
  --release-id abc123 \
  --approval engineering,security,product

# Emergency hotfix promotion
promote-release \
  --from-channel stable \
  --to-channel stable \
  --release-id hotfix-123 \
  --override-rollout 100 \
  --classification security-critical
```

## Kill Switch

### Immediate Stop
```json
{
  "rollout": {
    "percentage": 10,
    "killSwitch": true
  }
}
```

### Effects
- All clients immediately stop seeing the update
- In-progress downloads may complete but won't install
- Clients on newer version offered rollback
- Audit log entry created

### Activation
```bash
# Emergency kill switch
kill-switch --release-id abc123 --reason "Critical data loss bug"

# Or via API
POST /api/v1/releases/{id}/kill-switch
{
  "reason": "Critical security vulnerability",
  "activatedBy": "security-team"
}
```

## Emergency Procedures

### Hotfix Release
1. Create fix branch from stable tag
2. Apply minimal fix
3. Full CI pipeline
4. Emergency promotion to stable with 100% rollout
5. Classification: `security-critical`
6. Mandatory update flag if data loss risk

### Rollback Release
1. Identify last known-good release
2. Republish with 100% rollout
3. Kill switch on problematic release
4. Client auto-rollback on next check
5. Post-incident analysis

### Channel Freeze
```bash
freeze-channel --channel stable --reason "Investigating P0 regression"
```
- No new releases to frozen channel
- Existing rollouts continue
- Only emergency hotfixes allowed

## Client-Side Rollout Logic

### Eligibility Check
```typescript
function isEligibleForUpdate(
  manifest: UpdateManifest,
  client: ClientInfo
): boolean {
  // 1. Channel match
  if (manifest.channel !== client.channel) return false;
  
  // 2. Platform/architecture match
  const key = `${client.platform}-${client.architecture}`;
  if (!manifest.platforms[key]) return false;
  
  // 3. Version newer
  if (!isVersionNewer(client.version, manifest.version)) return false;
  
  // 4. Minimum version
  if (compareVersions(client.version, manifest.minimumVersion) < 0) return false;
  
  // 5. Kill switch
  if (manifest.rollout.killSwitch) return false;
  
  // 6. Rollout percentage
  if (!isInRollout(client.deviceId, manifest)) return false;
  
  // 6. Cohort targeting
  if (!matchesCohort(client, manifest.rollout.cohorts)) return false;
  
  return true;
}

function isInRollout(deviceId: string, manifest: UpdateManifest): boolean {
  if (manifest.rollout.percentage >= 100) return true;
  
  const hash = sha256(deviceId + manifest.releaseId);
  const bucket = parseInt(hash.slice(0, 8), 16) % 100;
  return bucket < manifest.rollout.percentage;
}
```

### Mandatory Updates
```json
{
  "security": {
    "classification": "security-critical",
    "mandatoryAfter": "2026-02-01T00:00:00Z"
  }
}
```
- Before date: Optional update
- After date: Mandatory, blocks app usage until updated
- Grace period for active sessions

## Monitoring & Metrics

### Rollout Health Dashboard
| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Download Success Rate | >99% | <98% |
| Install Success Rate | >99.5% | <99% |
| Crash Rate (7d) | <0.1% | >0.5% |
| Rollback Rate | <0.01% | >0.1% |
| Health Check Pass Rate | 100% | <100% |
| Mandatory Update Compliance | 100% | <95% |

### Real-Time Alerts
- PagerDuty for P0 rollout issues
- Slack for rollout phase transitions
- Email for daily rollout summaries

### Rollout Reports
- Daily: Phase progress, metrics, issues
- Weekly: Channel health, adoption trends
- Per-release: Full rollout timeline, metrics, lessons learned

## Client Communication

### Update Notifications
| State | UI | Timing |
|-------|-----|--------|
| Available | Toast + Settings badge | Immediate |
| Downloading | Progress bar | During download |
| Ready to Install | Modal (non-blocking) | After download |
| Installing | Full-screen progress | During install |
| Restart Required | Persistent banner | Post-install |
| Mandatory | Blocking modal | At deadline |
| Failed | Error dialog with retry | On failure |
| Rolled Back | Toast + explanation | Post-rollback |

### Release Notes Display
- Sanitized (no HTML/markdown execution)
- Truncated with "Read more" link
- Channel-appropriate detail level
- Links to full changelog

## Rollback Automation

### Automatic Rollback Triggers
| Trigger | Action |
|---------|--------|
| Health check failure | Auto-rollback |
| Crash loop detected (>3 in 10min) | Auto-rollback |
| Mandatory update failure | Auto-rollback + alert |
| Migration failure | Auto-rollback |

### Rollback Process
```typescript
async function automaticRollback(): Promise<void> {
  const rollbackInfo = await adapter.getRollbackInfo();
  if (!rollbackInfo.available) {
    alertOpsTeam('Rollback unavailable - manual intervention required');
    return;
  }
  
  const result = await adapter.rollback(rollbackInfo);
  if (result.success) {
    telemetry.record('auto_rollback_success', { fromVersion, toVersion });
  } else {
    alertOpsTeam(`Auto-rollback failed: ${result.error}`);
  }
}
```

## Testing Rollout Logic

### Simulation Tests
```typescript
// Test rollout assignment consistency
test('same device always gets same bucket', () => {
  const deviceId = 'device-123';
  const releaseId = 'release-456';
  const percentage = 10;
  
  const buckets = Array(1000).fill(null).map(() => 
    getBucket(deviceId, releaseId, percentage)
  );
  
  expect(new Set(buckets).size).toBe(1);
});

// Test percentage boundaries
test('percentage boundaries respected', () => {
  const deviceId = 'device-123';
  const releaseId = 'release-456';
  
  expect(isInRollout(deviceId, releaseId, 0)).toBe(false);
  expect(isInRollout(deviceId, releaseId, 100)).toBe(true);
});
```

### Canary Testing
- Internal team gets 100% of nightly/dev
- Alpha cohort gets 25% with opt-in
- Automated canary analysis (metrics comparison)
- Manual promotion gate after canary period

## Rollout Checklist

### Pre-Rollout
- [ ] All CI gates passing
- [ ] Security review complete
- [ ] Performance benchmarks within threshold (Master 71)
- [ ] SBOM generated and verified
- [ ] Provenance attestation verified
- [ ] Artifacts signed and notarized
- [ ] Manifest signed
- [ ] Rollout policy configured
- [ ] Kill switch tested
- [ ] Rollback tested
- [ ] Health checks validated
- [ ] Monitoring alerts configured
- [ ] Runbook reviewed
- [ ] On-call notified

### During Rollout
- [ ] Monitor health metrics dashboard
- [ ] Watch error rates and crash reports
- [ ] Check rollback rate
- [ ] Verify cohort targeting
- [ ] Confirm kill switch functional
- [ ] Communicate status to stakeholders

### Post-Rollout
- [ ] 100% rollout confirmed
- [ ] Metrics stable for 48 hours
- [ ] Rollback rate < threshold
- [ ] No P0/P1 issues
- [ ] Telemetry green
- [ ] Documentation updated
- [ ] Lessons learned recorded
- [ ] Next release planned

## Rollout Configuration API

### Update Channel Config
```bash
POST /api/v1/channels/stable/config
{
  "rolloutPolicy": {
    "percentage": 25,
    "cohorts": [
      { "id": "canary", "percentage": 100, "platforms": ["win32"] }
    ],
    "startDate": "2026-01-15T10:00:00Z"
  },
  "autoPromote": false,
  "requiredApprovals": 3
}
```

### Manual Rollout Advance
```bash
POST /api/v1/releases/abc123/rollout/advance
{
  "percentage": 50,
  "approvedBy": "release-manager"
}
```

### Emergency Override
```bash
POST /api/v1/releases/abc123/emergency-override
{
  "percentage": 100,
  "reason": "Security hotfix",
  "authorizedBy": "security-lead"
}
```