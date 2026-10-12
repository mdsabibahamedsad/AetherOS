# Performance Optimization Guide

This guide covers performance optimization for AetherOS production deployments.

## Performance Optimization Principles

1. **Minimize startup overhead** — Enable lazy loading, defer plugin initialization
2. **Reduce unnecessary allocations** — Cache tool definitions, reuse connections
3. **Batch I/O operations** — Buffer memory writes, batch state persistence
4. **Profile before optimizing** — Always measure before making changes

## Key Configuration Options

### Scheduler Tick Interval
```yaml
# config.yaml
kernel:
  tick_interval: 10  # Default 5s. Increase to reduce CPU overhead
```

### State Persistence
```yaml
# config.yaml
kernel:
  state_save_interval: 60  # Default 30s. Increase to reduce disk I/O
```

### Context Compression
```yaml
# config.yaml
compression:
  enabled: true
  target_turns: 50  # Keep more context before compression
```

### Memory Provider
```yaml
# config.yaml
memory:
  provider: ""  # Disable external memory provider if not needed
```

## Using the Optimizer

```python
from production.optimizer import Optimizer

optimizer = Optimizer()
results = optimizer.analyze_all()

for r in results:
    print(f"[{r.estimated_impact}] {r.name}: {r.suggestion}")
```

## Benchmarking Performance

```bash
# Profile CPU, memory, and I/O
aetheros profile all --duration 30

# Run benchmark suites
aetheros benchmark --iterations 10

# JSON output for machine parsing
aetheros benchmark --json
```

## Common Optimization Scenarios

### Slow Startup
- Disable unused plugins: `aetheros tools disable <toolset>`
- Use `--skip-context-files` flag
- Reduce number of enabled toolsets

### High Memory Usage
- Reduce session history window
- Enable aggressive context compression
- Configure memory provider write batching

### High CPU Usage
- Increase scheduler tick interval
- Reduce concurrent agent operations
- Enable result caching

### Slow Tool Execution
- Check network connectivity to API endpoints
- Reduce tool output limits
- Enable tool result caching
