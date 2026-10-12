# LTS Policy

## Version Support Lifecycle

```
                    ┌─────────────────────────────┐
                    │       Active Development     │
                    │   Bug fixes + new features   │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │       Maintenance Mode       │
                    │   Critical + security only   │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │        Security Mode         │
                    │   Security patches only      │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │       End of Life (EOL)      │
                    │   No further updates         │
                    └─────────────────────────────┘
```

### Phase Durations
| Phase | Duration | Begins | Updates |
|-------|----------|--------|---------|
| Active Development | 6 months | Release date | Full |
| Maintenance | 12 months | After active | Critical bugs + security |
| Security | 6 months | After maintenance | Security only |
| EOL | Indefinite | After security | None |

### EOL Notification Timeline
| Milestone | Action |
|-----------|--------|
| 12 months before EOL | Announcement in release notes |
| 6 months before EOL | In-app notification banner |
| 3 months before EOL | Persistent notification |
| 1 month before EOL | Weekly reminder |
| At EOL | App displays "unsupported" warning |

## Backport Policy

### What Gets Backported
1. **Critical (CVE):** All severity levels to all active channels
2. **High (CVE):** To stable and LTS within 7 days
3. **Medium (CVE):** To LTS within next security release
4. **Stability fixes:** To LTS if user-impacting

### What Does NOT Get Backported
- New features
- Refactoring
- Performance improvements (unless critical)
- Platform-specific enhancements
- Dependency upgrades (unless security)

## LTS Commitment

As an LTS maintainer, we commit to:
1. 24 months of support per LTS release
2. 6-month overlap between LTS releases
3. Security patches within 7 days of CVE disclosure
4. No breaking changes within an LTS series
5. Clear migration guides for LTS-to-LTS upgrades
6. Public release calendar with 12-month outlook

## Community Expectations

- Report bugs with reproducible steps
- Provide crash reports when requested
- Upgrade within support window
- Test beta releases before stable promotion
- Contribute patches for backport consideration

## Governance

| Role | Responsibility |
|------|---------------|
| LTS Manager | Release scheduling, backport decisions |
| Security Team | CVE triage, patch development |
| QA Team | Regression testing, validation |
| Documentation | Migration guides, changelogs |
| Community | Bug reports, testing feedback |

## Escalation Path

```
Bug Report → LTS Manager → Security Team (if CVE) → Patch → QA → Release
```

### SLA by Severity
| Severity | Response Time | Patch Time |
|----------|--------------|------------|
| Critical/CVE | 4 hours | 7 days |
| High | 24 hours | 14 days |
| Medium | 3 days | 30 days |
| Low | 7 days | Next release |
