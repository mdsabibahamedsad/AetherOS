# Troubleshooting Guide

Common issues and solutions for AetherOS production deployments.

## Quick Diagnostic

```bash
# Run all diagnostics
aetheros diagnostics

# Run detailed health check
aetheros health

# Get doctor recommendations
aetheros doctor

# Auto-fix issues
aetheros doctor --fix
```

## Common Issues

### 1. Slow Startup

**Symptoms:** AetherOS takes more than 5 seconds to start.

**Checks:**
```bash
aetheros profile cpu --duration 10
```

**Solutions:**
1. Disable unused toolsets: `aetheros tools disable <toolset>`
2. Reduce plugin count
3. Use `--skip-context-files` for faster initialization

### 2. High Memory Usage

**Symptoms:** > 800 MB RSS usage.

**Checks:**
```bash
aetheros profile memory
```

**Solutions:**
1. Reduce session history: configure compression aggressively
2. Disable unused memory providers
3. Reduce concurrent session count

### 3. Configuration Issues

**Symptoms:** "Provider not found" or "API key missing" errors.

**Checks:**
```bash
aetheros doctor
```

**Solutions:**
1. `aetheros doctor --fix` auto-corrects many issues
2. Run `aetheros setup` to configure providers
3. Check `~/.aetheros/.env` for correct API keys

### 4. Plugin Errors

**Symptoms:** Plugin failed to load or errors in logs.

**Checks:**
```bash
aetheros diagnostics --severity warning
```

**Solutions:**
1. Check `~/.aetheros/plugins/` for broken plugins
2. Disable problematic plugins: `aetheros tools disable <plugin_toolset>`
3. Reinstall plugins

### 5. Tool Not Available

**Symptoms:** Agent reports tool is not available.

**Checks:**
```bash
aetheros diagnostics  # Check tool registry section
```

**Solutions:**
1. Verify toolset is enabled: `aetheros tools list`
2. Check required API keys are set in `.env`
3. Ensure system dependencies are installed

### 6. Database Issues

**Symptoms:** State DB errors or WAL file growing unbounded.

**Checks:**
```bash
aetheros doctor --fix  # Auto-checkpoints and repairs
```

**Solutions:**
1. WAL checkpoint: `aetheros doctor --fix`
2. VACUUM if DB is large
3. Restore from backup if corruption persists

### 7. Gateway Platform Issues

**Symptoms:** Messaging platform not connecting or responding.

**Checks:**
```bash
aetheros health  # Check gateway component
```

**Solutions:**
1. Verify bot tokens in `.env`
2. Check platform-specific configuration in `config.yaml`
3. Review `~/.aetheros/logs/gateway.log` for errors

### 8. Version Mismatch

**Symptoms:** "Version inconsistency" warning.

**Checks:**
```bash
aetheros verify --compat
```

**Solutions:**
1. `aetheros update` to synchronize versions
2. If from git: ensure `git pull` is complete

## Getting Help

### Diagnostic Bundle

Generate a diagnostic bundle for support:

```bash
aetheros diagnostics --json > diagnostics.json
aetheros health --json > health.json
```

### Logs

```bash
# Export recent logs
aetheros logs --follow --level error > errors.log
```

## Known Limitations

- Kernel health checks verify module importability, not runtime state
- Stress tests use thread-level concurrency, not process-level isolation
- Chaos experiments are simulation-based and don't inject real network failures
- Migration validation requires both versions to be importable
