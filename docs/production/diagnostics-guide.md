# Diagnostics Guide

This guide covers running diagnostics on AetherOS production deployments.

## Overview

The diagnostics system provides comprehensive health and integrity checks for all AetherOS subsystems. Results are available in both human-readable and machine-readable formats.

## Quick Start

```bash
# Run all diagnostics
aetheros diagnostics

# Filter by severity
aetheros diagnostics --severity warning

# Machine-readable output
aetheros diagnostics --json
```

## Diagnostic Categories

| Category | What It Checks |
|----------|----------------|
| system | OS, platform, Python version |
| kernel | Kernel module availability |
| agent | Agent runtime state |
| configuration | Config file integrity, provider setup |
| network | API connectivity, DNS resolution |
| storage | Disk space, state DB integrity |
| memory | RSS usage, allocation patterns |
| plugins | Plugin load status, errors |
| tools | Tool registry health |
| gateway | Gateway platform connectivity |
| security | Advisory checks, permissions |
| performance | Startup time, throughput |

## Understanding Results

Each check has:
- **Status**: ok, warning, error, critical
- **Message**: Human-readable description
- **Recommendation**: Action to take if failed
- **Duration**: How long the check took

### Health Score

The health score (0.0–1.0) is computed from check severity:
- Errors/critical: reduces score by 1.0
- Warnings: reduces score by 0.5
- Info/ok: no impact

## Programmatic Usage

```python
from production.diagnostics import DiagnosticsEngine

engine = DiagnosticsEngine()
report = engine.run_all()

if report.error_count > 0:
    failed = report.get_failed_checks()
    for check in failed:
        print(f"FAILED: {check.name}")
        print(f"  Fix: {check.recommendation}")
```

## Health Monitoring

```bash
# Single health check
aetheros health

# Continuous monitoring
aetheros health --watch

# Health check with JSON output
aetheros health --json
```

## Python Health API

```python
from production.health import HealthChecker, HealthComponent

checker = HealthChecker()
report = checker.check_all()

print(f"Overall: {report.overall_status}")
print(f"Kernel: {checker.check_component(HealthComponent.KERNEL).status}")
```
