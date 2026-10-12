# Operations Manual

This manual covers day-to-day operations for AetherOS production deployments.

## Daily Operations

### Morning Check

```bash
# Quick health check
aetheros health

# Verify configuration
aetheros doctor

# Check active sessions
aetheros sessions  # or /sessions in CLI
```

### Monitoring

```bash
# Continuous health monitoring
aetheros health --watch

# Check running agents
/agents  # in CLI session
```

## CLI Reference

### Production Commands

| Command | Description |
|---------|-------------|
| `aetheros doctor` | Diagnose configuration and dependency issues |
| `aetheros doctor --fix` | Auto-fix detected issues |
| `aetheros health` | System health check |
| `aetheros health --watch` | Continuous health monitoring |
| `aetheros diagnostics` | Comprehensive system diagnostics |
| `aetheros diagnostics --severity error` | Show only errors |
| `aetheros benchmark` | Performance benchmarks |
| `aetheros profile all` | System profiling (CPU, memory, I/O) |
| `aetheros verify` | System integrity verification |
| `aetheros migrate-check` | Migration compatibility check |

### Session Management

| Command | Description |
|---------|-------------|
| `/new` | Start a new session |
| `/resume [name]` | Resume a previous session |
| `/status` | Show session info |
| `/usage` | Show token usage |
| `/stop` | Stop background processes |

### Configuration

| Command | Description |
|---------|-------------|
| `/model` | Switch models |
| `/config` | Show configuration |
| `/tools` | Manage toolsets |
| `/skills` | Manage skills |

## Maintenance

### Weekly Maintenance

```bash
# Run maintenance tasks
python -c "from production.maintenance import run_maintenance; print(run_maintenance().to_dict())"

# Check WAL file size
aetheros doctor --fix  # Auto-checkpoints WAL
```

### Monthly Maintenance

```bash
# Full system diagnostics
aetheros diagnostics --json > /var/log/aetheros/diagnostics-$(date +%Y%m).json

# Run regression tests
python -c "from production.regression import RegressionTester; t=RegressionTester(); r=t.run_all(); print(f'Passed: {r.passed_count}/{r.total_tests}')"

# Verify version consistency
python -c "from production.release_manager import ReleaseManager; m=ReleaseManager(); print(m.check_version_consistency())"
```

## Backup and Recovery

### Backup Configuration

```bash
# Backup AetherOS home directory
tar czf ~/aetheros-backup-$(date +%Y%m%d).tar.gz ~/.aetheros/
```

### Recovery

```bash
# Restore from backup
tar xzf ~/aetheros-backup-YYYYMMDD.tar.gz -C ~/

# Verify restored state
aetheros doctor
aetheros health
```

## Logging

```bash
# View logs
aetheros logs --follow

# View errors
aetheros logs --level error

# View specific session
aetheros logs --session <session-id>
```

## Resource Management

Monitor key resources:

| Resource | Alert Threshold | Action |
|----------|----------------|--------|
| Memory | > 800 MB RSS | Review session count, disable unused plugins |
| Disk | < 1 GB free | Run maintenance, clean logs, checkpoint WAL |
| CPU | > 80% sustained | Reduce concurrency, check for runaway agents |
| Errors | > 5% error rate | Investigate tool/API failures |
