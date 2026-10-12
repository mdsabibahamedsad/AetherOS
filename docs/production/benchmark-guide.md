# Benchmark Guide

This guide covers running and interpreting benchmarks for AetherOS.

## Overview

The benchmark system provides repeatable, machine-readable performance measurements. Benchmarks cover startup time, memory usage, workflow execution, plugin loading, and more.

## Running Benchmarks

```bash
# Run all benchmark suites
aetheros benchmark

# Run a specific suite
aetheros benchmark startup
aetheros benchmark memory
aetheros benchmark workflow
aetheros benchmark plugins

# Control iteration count
aetheros benchmark --iterations 10

# JSON output
aetheros benchmark --json

# Custom output directory
aetheros benchmark --output ./benchmarks
```

## Benchmark Suites

### Startup Suite
Measures time to boot kernel, discover components, and initialize services.

### Memory Suite
Measures RSS usage at various stages: baseline, after plugin load, after agent init.

### Workflow Suite
Measures end-to-end workflow execution throughput.

### Plugin Suite
Measures plugin discovery and initialization latency.

## Output Format

Results are saved as JSON files in `/tmp/aetheros-benchmarks/`:

```json
{
  "name": "startup",
  "benchmarks": [{
    "name": "kernel_boot",
    "metrics": {
      "avg_ms": 245.3,
      "p95_ms": 312.1,
      "median_ms": 198.7
    }
  }]
}
```

## Programmatic Benchmarks

```python
from production.benchmark import BenchmarkRunner, BenchmarkSuite

runner = BenchmarkRunner()

suite = BenchmarkSuite(name="custom", description="Custom benchmarks")

# Add benchmarks
result = runner.benchmark(
    "my_operation",
    lambda: do_work(),
    iterations=5,
    warmup=2,
)
suite.add_result(result)

# Save results
suite.save("./results/my-benchmark.json")
```

## Comparing Results

Load previous results for comparison:

```python
from production.benchmark import BenchmarkSuite

previous = BenchmarkSuite.load("/tmp/aetheros-benchmarks/startup_1234567890.json")
current = BenchmarkSuite.load("/tmp/aetheros-benchmarks/startup_1234598765.json")

for bp, bc in zip(previous.benchmarks, current.benchmarks):
    delta = bc.metrics["avg_ms"] - bp.metrics["avg_ms"]
    direction = "↑" if delta > 0 else "↓"
    print(f"{bp.name}: {bp.metrics['avg_ms']:.1f} → {bc.metrics['avg_ms']:.1f} ms {direction}")
```
