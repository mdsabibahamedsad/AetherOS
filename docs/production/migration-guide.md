# Migration Guide

This guide covers upgrading AetherOS between versions with backward compatibility.

## Overview

Migration validation checks configuration, plugin, state, and API compatibility between source and target AetherOS versions. Run `aetheros migrate-check` before upgrading any production deployment.

## Quick Start

```bash
# Check migration from current to current version
aetheros migrate-check

# Check migration between specific versions
aetheros migrate-check 0.10.0 0.11.0

# Machine-readable output
aetheros migrate-check --json
```

## Migration Checks

The migration validator performs these checks:

| Check | Description |
|-------|-------------|
| config_version | Config schema version compatibility |
| plugin_errors | Plugin integrity and compatibility |
| state_db_integrity | State database schema compatibility |
| sdk_compatibility | SDK version range compatibility |

## Migration Procedure

### 1. Pre-Migration Validation

```bash
# Validate current state
aetheros verify --compat

# Check migration compatibility
aetheros migrate-check <current> <target>

# Run diagnostics
aetheros diagnostics
```

### 2. Backup State

```bash
# Backup AetherOS home directory
cp -r ~/.aetheros ~/.aetheros.backup

# Export session data (recommended)
aetheros sessions export
```

### 3. Perform Upgrade

```bash
# Update Aetheros
aetheros update

# Or via pip
pip install --upgrade aetheros
```

### 4. Post-Migration Validation

```bash
# Run diagnostics to verify everything works
aetheros diagnostics

# Check health
aetheros health

# If issues detected, run auto-fix
aetheros doctor --fix
```

## Handling Migration Issues

### Config Version Mismatch
```bash
aetheros doctor --fix  # Auto-migrates config
```

### Plugin Compatibility
```bash
aetheros plugins list  # Check plugin status
aetheros plugins disable <problematic-plugin>  # Disable incompatible plugins
```

### State DB Issues
```bash
aetheros doctor --fix  # Auto-repairs state DB
```

## Compatible vs Breaking Changes

### Compatible Changes
- Adding new config keys (deep-merge handles defaults)
- Adding new tools to the tool registry
- Adding new event types to the event bus
- Plugin API additions

### May Require Migration
- Config schema version bumps
- State database schema changes
- Plugin API changes
- Deprecated feature removal

## Programmatic Migration Check

```python
from production.migration_validator import MigrationValidator

validator = MigrationValidator()
report = validator.validate("0.10.0", "0.11.0")

for issue in report.get_blocking_issues():
    print(f"BLOCKING: {issue.recommendation}")

if report.overall_compatible:
    print("Migration is safe to proceed")
```
