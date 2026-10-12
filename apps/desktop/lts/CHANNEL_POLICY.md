# Channel Policy

## Channel Definitions

### Nightly Channel
- **Purpose:** Continuous integration, bleeding-edge features
- **Audience:** Developers, testers, contributors
- **Update frequency:** Daily (06:00 UTC)
- **Support:** None — use at your own risk
- **Stability:** May crash, lose data, break workflows
- **Telemetry:** Required (development metrics)
- **Auto-update:** Always on

### Beta Channel
- **Purpose:** Feature validation, early feedback
- **Audience:** Early adopters, power users
- **Update frequency:** Weekly
- **Support:** Best-effort via GitHub Issues
- **Stability:** Feature-complete but may have bugs
- **Telemetry:** Required (quality metrics)
- **Auto-update:** Optional

### Stable Channel
- **Purpose:** General availability, daily use
- **Audience:** All users
- **Update frequency:** Monthly
- **Support:** GitHub Issues + community forums
- **Stability:** Production-ready, tested
- **Telemetry:** Opt-in
- **Auto-update:** Default on, can disable

### LTS Channel
- **Purpose:** Enterprise deployments, long-term stability
- **Audience:** Organizations, enterprise customers
- **Update frequency:** Security-only after active phase
- **Support:** Dedicated SLA, 24-month window
- **Stability:** Maximum — no breaking changes
- **Telemetry:** Opt-in
- **Auto-update:** Default on (security only)

### Security Patch Channel
- **Purpose:** Emergency vulnerability fixes
- **Audience:** All active channel users
- **Update frequency:** As needed
- **Trigger:** CVE disclosure, responsible disclosure
- **Turnaround:** 7 days for critical, 14 for high

### Emergency Hotfix Channel
- **Purpose:** Zero-day exploits, critical data loss bugs
- **Audience:** Affected users
- **Update frequency:** Within 24-48 hours
- **Trigger:** Confirmed active exploitation, data loss
- **Turnaround:** Hotfix within 24 hours

## Channel Eligibility

| Feature | Nightly | Beta | Stable | LTS |
|---------|---------|------|--------|-----|
| New features | ✅ | ✅ | ✅ | ❌ |
| API additions | ✅ | ✅ | ✅ | ⚠️ (back-compat) |
| API breaking changes | ✅ | ⚠️ (deprecation) | ❌ | ❌ |
| Dependency updates | ✅ | ✅ | ⚠️ | Security-only |
| Security patches | ✅ | ✅ | ✅ | ✅ |
| Database migrations | ✅ | ✅ | ✅ | ✅ (tested) |

## Promotion Criteria

### Beta → Stable
- [ ] All tests pass (unit + integration + e2e)
- [ ] No high-severity open bugs
- [ ] Security scan clean (no high+)
- [ ] Performance regression < 5%
- [ ] Documentation updated
- [ ] Migration guide complete (if applicable)
- [ ] 7 days in beta with no critical issues

### Stable → LTS
- [ ] 30 days in stable with no critical issues
- [ ] All security patches applied
- [ ] LTS-specific testing complete
- [ ] Enterprise deployment verified
- [ ] Backward compatibility confirmed
- [ ] Migration guide for prev LTS
- [ ] LTS lifecycle documented

## Channel Switching

```typescript
export function canSwitchChannel(from: LTSChannel, to: LTSChannel): boolean {
  if (from === to) return true
  if (to === 'emergency-hotfix' || to === 'security-patch') return true
  if (from === 'nightly' && to === 'stable') return true
  if (from === 'beta' && to === 'stable') return true
  if (from === 'stable' && to === 'lts') return true
  if (from === 'lts') return false // Cannot downgrade from LTS
  if (to === 'beta' || to === 'nightly') return true // Can always go unstable
  return false
}
```

## Update Attribution
All updates include:
- Version number
- Channel tag
- Build timestamp
- Signed checksum
- Release notes link
- Migration guide link (if applicable)
