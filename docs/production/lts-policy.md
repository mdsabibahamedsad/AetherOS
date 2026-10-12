# Long-Term Support (LTS) Policy

This document defines the Long-Term Support policy for AetherOS.

## Version Scheme

AetherOS uses [Semantic Versioning](https://semver.org/) (MAJOR.MINOR.PATCH) combined with CalVer dates for releases.

- **MAJOR**: Breaking changes (API incompatibility)
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

## LTS Release Cadence

| Version | Support Type | Duration | Frequency |
|---------|-------------|----------|-----------|
| Current | Standard | 6 months | Every 2-4 weeks |
| Previous | LTS | 12 months | Patch-only |
| Stable | LTS | 24 months | Security + critical fixes |
| Legacy | Deprecated | No support | Migration recommended |

## Supported Versions

| Version | Status | Release Date | End of Support | Security Fixes | Bug Fixes |
|---------|--------|-------------|---------------|---------------|-----------|
| 0.16.x | Current | Jun 2026 | Dec 2026 | ✓ | ✓ |
| 0.15.x | LTS | May 2026 | May 2027 | ✓ | ✓ |
| 0.14.x | LTS | Apr 2026 | Apr 2027 | ✓ | Critical only |
| 0.13.x | Deprecated | Mar 2026 | Sep 2026 | ✗ | ✗ |
| ≤ 0.12.x | End of Life | — | — | ✗ | ✗ |

## Security Fix Policy

- **Critical vulnerabilities**: Patched within 48 hours for all supported versions
- **High vulnerabilities**: Patched within 1 week for Current and LTS versions
- **Moderate vulnerabilities**: Patched in next scheduled release for Current version
- **Low vulnerabilities**: Patched in next minor release

## API Stability

### Stable API (guaranteed backward compatibility)
- `sdk/*` module exports
- `tools/registry` public interface
- `kernel/event_bus` topic contracts
- Plugin registration API (`register`, `register_tool`, lifecycle hooks)
- CLI exit codes and status messages
- Configuration file format (`config.yaml`)

### Unstable API (may change between minor versions)
- `kernel/*` internal module structure
- `production/*` module interfaces (production GA module)
- Plugin internal APIs (non-registration interfaces)
- CLI output formatting

### Private API (may change without notice)
- Internal helper modules and functions
- Underscore-prefixed functions and methods
- Test utilities and fixtures

## Deprecation Schedule

1. **Announcement**: Feature marked deprecated in release notes
2. **Warning period**: Feature remains functional for 3 minor releases
3. **Removal**: Feature removed in next major release

## Plugin Compatibility

Plugins declare their compatible AetherOS version range in their manifest:

```yaml
# plugin.yaml
aetheros_version: ">=0.14.0,<0.17.0"
```

The compatibility checker validates this at load time:

```bash
aetheros verify --compat
```

## Migration Between LTS Versions

```bash
# 1. Check current version
aetheros version

# 2. Validate migration path
aetheros migrate-check 0.14.0 0.15.0

# 3. Update
aetheros update

# 4. Verify
aetheros verify --compat
```

## Release Process

1. Version bump (semver)
2. Build artifacts (sdist + wheel)
3. Checksum generation
4. Release notes compilation
5. Pre-release validation
6. GitHub release creation
7. PyPI publication
8. Post-release monitoring (48h)

See [Release Process](./release-process.md) for details.
