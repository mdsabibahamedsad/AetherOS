# AetherOS Release Runbook

## Overview

This runbook provides step-by-step procedures for releasing AetherOS updates across all platforms and channels.

## Release Types

| Type | Trigger | Channel | Approval |
|------|---------|---------|----------|
| Nightly | Daily scheduled | nightly | Automated |
| Development | PR merged to main | dev | Automated |
| Alpha | Feature complete | alpha | Engineering |
| Beta | Feature freeze | beta | Engineering + Security |
| Stable | Release candidate | stable | Engineering + Security + Product |
| Hotfix | Critical fix | stable | Engineering + Security |
| Enterprise | LTS branch | enterprise | Engineering + Security + Customer |

---

## Pre-Release Checklist

### 1. Code Complete
- [ ] All features merged to target branch
- [ ] All PRs approved and merged
- [ ] No open P0/P1 bugs on target branch
- [ ] CHANGELOG.md updated
- [ ] Version bumped (semver)

### 2. Quality Gates
- [ ] All tests pass (unit, integration, e2e)
- [ ] Type checking clean (`npm run typecheck`, `mypy`)
- [ ] Linting clean (`npm run lint`, `ruff`)
- [ ] Security audit clean (`npm audit`, `pip-audit`)
- [ ] Secret scanning clean
- [ ] Dependency audit clean
- [ ] SAST scan clean

### 3. Platform Builds
- [ ] Windows NSIS built and tested
- [ ] Windows MSI built and tested
- [ ] macOS DMG built and tested
- [ ] macOS PKG built and tested
- [ ] macOS Universal binary built
- [ ] Linux AppImage built and tested
- [ ] Linux DEB built and tested
- [ ] Linux RPM built and tested
- [ ] Linux Flatpak built and tested
- [ ] Web build deployed to staging

### 4. Signing & Notarization
- [ ] Windows Authenticode signing (EV cert)
- [ ] macOS Developer ID signing
- [ ] macOS Notarization + Stapling
- [ ] Linux GPG signing (DEB/RPM)
- [ ] Linux AppImage signing
- [ ] Flatpak OSTree signing

### 5. Artifacts & Metadata
- [ ] SHA-256 hashes generated for all artifacts
- [ ] SBOM generated (CycloneDX + SPDX)
- [ ] SLSA provenance generated
- [ ] Manifest created and signed
- [ ] Release notes finalized

---

## Release Procedure

### Standard Release (Stable Channel)

#### Phase 1: Prepare (T-2 days)
```bash
# 1. Create release branch
git checkout main
git pull origin main
git checkout -b release/v1.2.3

# 2. Bump version
npm run release:bump -- --type patch --channel stable

# 3. Update CHANGELOG
# Edit CHANGELOG.md with release notes

# 4. Commit and tag
git add .
git commit -m "chore: release v1.2.3"
git tag -a v1.2.3 -m "Release v1.2.3"
git push origin release/v1.2.3 --tags
```

#### Phase 2: CI/CD Pipeline (T-1 day)
```bash
# Pipeline automatically triggers on tag push
# Monitor: https://github.com/aetheros/aetheros/actions

# Required stages (must all pass):
# ✅ test
# ✅ security
# ✅ build (all platforms)
# ✅ package (all platforms)
# ✅ sign (all platforms)
# ✅ hash-sbom
# ✅ publish-artifacts
# ✅ publish-manifest
```

#### Phase 2: CI/CD Pipeline Monitoring

```bash
# Watch pipeline progress
gh run watch --repo aetheros/aetheros

# If any stage fails:
# 1. Check failure logs
# 2. Fix issue
# 3. Re-run failed job or push new tag

# Critical: Do NOT proceed if any stage fails
```

#### Phase 3: Canary Rollout (T=0)
```bash
# After pipeline completes successfully:

# 1. Verify manifest published
curl https://updates.aetheros.com/api/v1/updates/win32/x64/stable

# 2. Configure canary (1%)
aetheros-update-server configure-channel \
  --channel stable \
  --percentage 1 \
  --start-date "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# 3. Announce canary
# Post in #releases channel
```

#### Phase 4: Canary Monitoring (T+24h)
```bash
# After 24 hours, check metrics:
aetheros-update-server metrics --channel stable --release-id v1.2.3

# Key metrics to verify:
# - install_failure_rate < 0.01 (1%)
# - crash_rate < 0.001 (0.1%)
# - rollback_rate < 0.001 (0.1%)
# - health_check_pass_rate == 1.0 (100%)

# If ANY metric exceeds threshold:
aetheros-update-server kill-switch --release-id v1.2.3 --reason "Canary metrics exceeded threshold"
# Investigate, fix, re-release
```

#### Phase 5: Progressive Rollout
```bash
# Phase 1: 5% (after canary passes)
aetheros-update-server advance-rollout --release-id v1.2.3 --percentage 5

# Wait 48 hours, check metrics
aetheros-update-server metrics --channel stable --release-id v1.2.3

# Phase 2: 25% (if metrics good)
aetheros-update-server advance-rollout --release-id v1.2.3 --percentage 25

# Wait 1 week, check metrics

# Phase 3: 100% (if metrics good)
aetheros-update-server advance-rollout --release-id v1.2.3 --percentage 100
```

#### Phase 6: Post-Release (T+2 weeks)
```bash
# 1. Verify 100% rollout complete
aetheros-update-server rollout-status --channel stable --release-id v1.2.3

# 2. Monitor for 2 weeks
# - No P0/P1 regressions
# - Error rates stable
# - Adoption curve as expected

# 3. Close release
# - Update release notes with final metrics
# - Archive canary/beta branches
# 3. Plan next release
```

---

## Hotfix Release (Emergency)

### When to Use
- Critical security vulnerability (CVSS ≥ 9.0)
- Data loss/corruption bug
- Complete service outage
- Regression causing widespread failures

### Procedure (Target: < 4 hours)

```bash
# 1. Create hotfix branch from stable tag
git checkout v1.2.3
git checkout -b hotfix/cve-2026-xxxx

# 2. Apply minimal fix
# - Single commit if possible
# - No refactoring
# - No new features

# 3. Test fix locally
npm run test:related
npm run build:quick

# 4. Bump version (patch)
npm run release:bump -- --type patch --channel stable
# Version becomes 1.2.4

# 5. Commit and tag
git add .
git commit -m "fix: CVE-2026-XXXX - brief description"
git tag -a v1.2.4 -m "Hotfix v1.2.4: CVE-2026-XXXX"
git push origin hotfix/cve-2026-xxxx --tags

# 6. Pipeline runs (abbreviated for hotfix)
# - test (critical tests only)
# - security (full)
# - build (all platforms)
# - sign (all platforms)
# - hash-sbom
# - publish-artifacts
# - publish-manifest

# 7. IMMEDIATE 100% rollout (override)
aetheros-update-server emergency-override \
  --release-id v1.2.4 \
  --percentage 100 \
  --reason "Security hotfix: CVE-2026-XXXX" \
  --classification security-critical \
  --authorized-by security-lead

# 8. Notify
# - Security advisory published
# - Users notified via in-app modal
# - Enterprise customers emailed
```

---

## Beta/Alpha Release

### Beta Release (Every 2 weeks)

```bash
# 1. Branch from main
git checkout main
git pull origin main
git checkout -b beta/v1.3.0-beta.1

# 2. Bump to beta
npm run release:bump -- --type prerelease --preid beta --channel beta

# 2. Push branch (triggers beta pipeline)
git push origin beta/v1.3.0-beta.1

# Pipeline: test → build → package → sign → publish to beta channel
# Auto-rollout: 25% → 100% over 1 week

# 3. Monitor beta metrics
aetheros-update-server metrics --channel beta --duration 7d
```

### Alpha Release (Weekly)

```bash
# Similar to beta but:
# - Channel: alpha
# - Rollout: 25% → 100% over 3 days
# - Less stringent gates (no product approval)
# - Auto-promote to beta after 1 week stable
```

---

## Nightly Release (Automated)

```yaml
# .github/workflows/nightly.yml
# Runs daily at 2 AM UTC from main branch
# Version: 1.3.0-nightly.20260115
# Channel: nightly
# Rollout: 100% immediate
# No gates (failures just mean no nightly that day)
```

---

## Enterprise Release (Quarterly LTS)

```bash
# 1. Branch from stable
git checkout v1.2.3
git checkout -b enterprise/v1.2-lts

# 2. Apply only critical fixes
# - Security patches
# - Data integrity fixes
# - Compatibility fixes

# 3. Version: 1.2.3-lts.1
npm run release:bump -- --type prerelease --preid lts --channel enterprise

# 3. Pipeline: Full validation + compliance checks
# - Extended test suite
# - Compliance scans (SOC2, etc.)
# - Long-term support validation

# 4. Channel: enterprise
# Rollout: 100% controlled by enterprise admin
```

---

## Rollback Procedures

### Release Rollback (Failed Release)

```bash
# 1. Kill switch
aetheros-update-server kill-switch --release-id v1.2.3 --reason "P0 regression"

# 2. Revoke release
aetheros-update-server revoke --release-id v1.2.3 --reason "P0 regression: description"

# 3. Promote previous stable
aetheros-update-server promote \
  --from-channel stable \
  --to-channel stable \
  --release-id v1.2.2 \
  --override-rollout 100

# 4. Investigate and fix
# Create hotfix branch from v1.2.2
```

### Hotfix Rollback (Failed Hotfix)

```bash
# Same as above but hotfix-specific
aetheros-update-server kill-switch --release-id v1.2.4 --reason "Hotfix regression"
aetheros-update-server revoke --release-id v1.2.4
aetheros-update-server promote --from-channel stable --to-channel stable --release-id v1.2.3 --override-rollout 100
```

### Channel Freeze

```bash
# Freeze stable channel
aetheros-update-server freeze-channel --channel stable --reason "Investigating P0"

# Unfreeze after investigation
aetheros-update-server unfreeze-channel --channel stable
```

---

## Release Communication

### Internal Notification

```markdown
# Release Announcement Template

## AetherOS v1.2.3 Released

**Channel:** stable
**Release ID:** v1.2.3
**Commit:** abc123def456
**Date:** 2026-01-15

### Highlights
- ✨ New feature: ...
- 🐛 Fixed: ...
- 🔒 Security: ...
- ⚡ Performance: ...

### Rollout Plan
- T+0h: Canary 1% (internal)
- T+24h: 5% (canary passed)
- T+72h: 25%
- T+1w: 100%

### Links
- Release notes: https://github.com/aetheros/aetheros/releases/tag/v1.2.3
- Manifest: https://updates.aetheros.com/api/v1/updates/win32/x64/stable
- Artifacts: https://releases.aetheros.com/v1.2.3/
- SBOM: https://releases.aetheros.com/v1.2.3/sbom.json

### Action Required
- [ ] Engineering: Monitor canary metrics
- [ ] Support: Update knowledge base
- [ ] Marketing: Prepare blog post
- [ ] Enterprise: Notify enterprise customers
```

### User-Facing Changelog

```markdown
# AetherOS v1.2.3

## 🎉 New Features
- **Smart Memory Search**: Natural language queries across all memories
- **Agent Templates**: Pre-built agent configurations for common tasks

## 🐛 Bug Fixes
- Fixed memory leak in long-running conversations
- Fixed crash when importing large skill packs
- Fixed WebSocket reconnection on network changes

## 🔒 Security
- Updated Electron to 40.10.6 (CVE-2026-XXXX)
- Updated dependencies with security patches

## ⚡ Performance
- 40% faster cold startup
- 20% reduction in memory usage
- Faster agent initialization

## 📦 Download
- Windows: [NSIS](...) | [MSI](...)
- macOS: [DMG](...) | [PKG](...)
- Linux: [AppImage](...) | [DEB](...) | [RPM](...) | [Flatpak](...)
- Web: Automatic update

## 🔧 For Developers
- New SDK method: `agent.createTemplate()`
- Updated TypeScript definitions
- Migration guide: v1.1 → v1.2
```

---

## Post-Release Checklist

### Immediate (T+0 to T+1h)
- [ ] Pipeline completed successfully
- [ ] Manifest published and accessible
- [ ] Artifacts downloadable from CDN
- [ ] Canary rollout configured (1%)
- [ ] Monitoring alerts active
- [ ] On-call notified
- [ ] Internal announcement sent

### Short-term (T+24h to T+1w)
- [ ] Canary metrics reviewed (T+24h)
- [ ] Rollout advanced to 5% (T+24h)
- [ ] Rollout advanced to 25% (T+72h)
- [ ] Rollout advanced to 100% (T+1w)
- [ ] No P0/P1 issues reported
- [ ] Error rates within threshold
- [ ] Rollback rate < 0.1%

### Long-term (T+2w)
- [ ] Full rollout confirmed
- [ ] Metrics stable for 2 weeks
- [ ] No regressions reported
- [ ] Documentation updated
- [ ] Lessons learned documented
- [ ] Next release planned

---

## Emergency Contacts

| Role | Name | Contact | Escalation |
|------|------|---------|------------|
| Release Manager | | | Primary |
| Security Lead | | | Security issues |
| Engineering Lead | | | Technical issues |
| Product Lead | | | Feature decisions |
| On-Call Engineer | | | After hours |
| Security Team | | security@aetheros.com | Security incidents |

---

## Versioning Rules

### Semantic Versioning
```
MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]

MAJOR: Breaking changes, incompatible API
MINOR: New features, backward compatible
PATCH: Bug fixes, backward compatible
PRERELEASE: alpha, beta, rc, nightly, lts
BUILD: CI build metadata
```

### Channel Versioning
| Channel | Format | Example |
|---------|--------|---------|
| nightly | MAJOR.MINOR.PATCH-nightly.YYYYMMDD | 1.3.0-nightly.20260115 |
| dev | MAJOR.MINOR.PATCH-dev.N | 1.3.0-dev.42 |
| alpha | MAJOR.MINOR.PATCH-alpha.N | 1.3.0-alpha.1 |
| beta | MAJOR.MINOR.PATCH-beta.N | 1.3.0-beta.3 |
| stable | MAJOR.MINOR.PATCH | 1.2.3 |
| enterprise | MAJOR.MINOR.PATCH-lts.N | 1.2.3-lts.1 |

### Version Bumping
```bash
# Patch (bug fix)
npm run release:bump -- --type patch --channel stable
# 1.2.3 → 1.2.4

# Minor (new feature)
npm run release:bump -- --type minor --channel stable
# 1.2.3 → 1.3.0

# Major (breaking)
npm run release:bump -- --type major --channel stable
# 1.2.3 → 2.0.0

# Prerelease
npm run release:bump -- --type prerelease --preid beta --channel beta
# 1.2.3 → 1.3.0-beta.1
```

---

## Release Artifacts Checklist

### Per Platform
| Platform | Artifacts | Signatures | Hashes | SBOM |
|----------|-----------|------------|--------|------|
| Windows x64 | NSIS (.exe), MSI (.msi) | Authenticode | SHA-256 | ✅ |
| Windows arm64 | NSIS (.exe), MSI (.msi) | Authenticode | SHA-256 | ✅ |
| macOS x64 | DMG, PKG, ZIP | Developer ID + Notarization | SHA-256 | ✅ |
| macOS arm64 | DMG, PKG, ZIP | Developer ID + Notarization | SHA-256 | ✅ |
| macOS universal | DMG, PKG, ZIP | Developer ID + Notarization | SHA-256 | ✅ |
| Linux x64 | AppImage, DEB, RPM, Flatpak | GPG + AppImageKit | SHA-256 | ✅ |
| Linux arm64 | AppImage, DEB, RPM, Flatpak | GPG + AppImageKit | SHA-256 | ✅ |
| Web | Static assets | SRI + CSP | SHA-256 | ✅ |

### Manifest & Metadata
- [ ] Signed manifest.json published
- [ ] hashes.txt with all SHA-256
- [ ] sbom.json (CycloneDX)
- [ ] provenance.intoto.jsonl (SLSA)
- [ ] Release notes published
- [ ] Changelog updated

---

## Quality Gates

### Must Pass Before Release
| Gate | Command | Threshold |
|------|---------|-----------|
| Unit tests | `pytest tests/ -x` | 100% pass |
| Integration tests | `pytest tests/integration/` | 100% pass |
| E2E tests | `npm run test:ui` | 100% pass |
| Type check (Python) | `mypy .` | 0 errors |
| Type check (TS) | `npm run typecheck` | 0 errors |
| Lint (Python) | `ruff check .` | 0 errors |
| Lint (TS) | `npm run lint` | 0 errors |
| Security audit (Python) | `pip-audit` | 0 vulnerabilities |
| Security audit (Node) | `npm audit` | 0 high/critical |
| Secret scan | `trufflehog` | 0 secrets |
| Dependency audit | `pip-audit` / `npm audit` | 0 high/critical |
| SAST | CodeQL | 0 critical/high |

### Performance Gates (Master 71)
| Metric | Baseline | Threshold |
|--------|----------|-----------|
| CLI startup | 839ms | < 1000ms |
| Database connection | 0.19ms | < 1ms |
| Bundle size (JS) | 23.6MB | < 10MB (needs work) |
| Memory leak test | 0 MB growth | < 10MB/hr |

### Security Gates (Master 72)
| Check | Required |
|-------|----------|
| All artifacts signed | ✅ |
| All artifacts hashed | ✅ |
| Manifest signed | ✅ |
| Notarization (macOS) | ✅ |
| SBOM generated | ✅ |
| Provenance generated | ✅ |
| No critical vulnerabilities | ✅ |
| Certificate pinning verified | ✅ |

---

## Release Metrics Dashboard

### Key Metrics to Monitor
| Metric | Source | Target |
|--------|--------|--------|
| Install success rate | Telemetry | > 99.5% |
| Download success rate | CDN logs | > 99% |
| Crash rate (7d) | Crash reporter | < 0.1% |
| Rollback rate | Telemetry | < 0.01% |
| Adoption rate | Telemetry | > 80% in 2 weeks |
| Mandatory compliance | Telemetry | 100% |

### Dashboards
- **Grafana**: `https://grafana.aetheros.com/d/releases`
- **Datadog**: `https://app.datadoghq.com/dashboard/releases`
- **Custom**: `https://updates.aetheros.com/admin/releases/{id}`

---

## Appendix: Release Commands Quick Reference

```bash
# Version bump
npm run release:bump -- --type patch|minor|major|prerelease --channel stable|beta|alpha|nightly

# Create release on server
aetheros-update-server create-release \
  --version 1.2.3 \
  --channel stable \
  --artifacts ./dist \
  --commit $(git rev-parse HEAD) \
  --release-notes "$(cat RELEASE_NOTES.md)"

# Publish release
aetheros-update-server publish --release-id <id>

# Configure rollout
aetheros-update-server configure-channel \
  --channel stable \
  --percentage 1 \
  --start-date "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Advance rollout
aetheros-update-server advance-rollout \
  --release-id v1.2.3 \
  --percentage 25

# Emergency override
aetheros-update-server emergency-override \
  --release-id v1.2.4 \
  --percentage 100 \
  --reason "Security hotfix" \
  --authorized-by security-lead

# Kill switch
aetheros-update-server kill-switch --release-id v1.2.3 --reason "Reason"

# Revoke release
aetheros-update-server revoke --release-id v1.2.3 --reason "Reason"

# Promote between channels
aetheros-update-server promote \
  --from-channel beta \
  --to-channel stable \
  --release-id v1.2.3 \
  --approvals engineering,security,product

# Freeze/unfreeze channel
aetheros-update-server freeze-channel --channel stable --reason "Investigating"
aetheros-update-server unfreeze-channel --channel stable

# Metrics
aetheros-update-server metrics --channel stable --release-id v1.2.3
aetheros-update-server rollout-status --channel stable --release-id v1.2.3
```