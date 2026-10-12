# Performance Monitoring System

## Architecture

```
┌─────────────────────────────────────────────┐
│           Performance Monitor                │
│  Collects snapshots every 60s                │
│  Stores up to 1000 snapshots                 │
│  Provides average calculations               │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│         Performance Dashboard                │
│  Real-time: CPU │ Memory │ GPU │ Disk        │
│  Historical: Charts │ Trends │ Analysis      │
└─────────────────────────────────────────────┘
```

## Metrics Collected

### Startup
| Metric | Description |
|--------|-------------|
| Cold Start | Time from launch to interactive (first launch) |
| Warm Start | Time from launch to interactive (subsequent) |
| Main Process Init | Main process initialization time |
| Preload Exec | Preload script execution time |
| First Paint | Time to first contentful paint |
| Time to Interactive | Time to full interactivity |

### CPU
| Metric | Description |
|--------|-------------|
| Overall | Total CPU usage percentage |
| Process | App process CPU usage |
| System | System-wide CPU usage |
| Cores | Available CPU cores |

### GPU
| Metric | Description |
|--------|-------------|
| Usage | GPU utilization percentage |
| Memory Used | GPU memory used |
| Memory Total | Total GPU memory |
| Temperature | GPU temperature (if available) |

### Memory
| Metric | Description |
|--------|-------------|
| Heap Used | JavaScript heap used |
| Heap Total | JavaScript heap total |
| System Used | System memory used by app |
| System Total | Total system memory |
| Process | Process memory usage |

### Disk
| Metric | Description |
|--------|-------------|
| Read Speed | Disk read speed |
| Write Speed | Disk write speed |
| Usage | Disk space used |
| Total | Total disk space |

### Extensions
| Metric | Description |
|--------|-------------|
| Loaded | Number of loaded extensions |
| Active | Number of active extensions |
| Failed | Number of failed extensions |
| Memory Usage | Combined extension memory |

### Models
| Metric | Description |
|--------|-------------|
| Loaded | Number of loaded models |
| Active Inferences | Currently running inferences |
| Average Latency | Average inference latency |
| Cache Hit Rate | Model cache hit rate |

### Automation
| Metric | Description |
|--------|-------------|
| Active Workflows | Currently running workflows |
| Completed Today | Workflows completed today |
| Failed Today | Workflows failed today |
| Average Duration | Average workflow duration |

## Dashboard Views

### Live View
- Real-time CPU, memory, GPU gauges
- Process list with per-process metrics
- Alert panel for threshold violations

### Timeline View
- Historical charts for each metric
- Adjustable time range (1h, 6h, 24h, 7d, 30d)
- Zoom and pan controls

### Comparison View
- Side-by-side metric comparison
- Before/after optimization comparison
- Version-to-version comparison

## Collection Configuration

```typescript
interface PerformanceConfig {
  collectionInterval: number  // Milliseconds (default: 60000)
  maxHistory: number          // Max snapshots (default: 1000)
  enableGPU: boolean          // Collect GPU metrics
  enableDisk: boolean         // Collect disk metrics
  retentionDays: number       // Days to retain history
}
```
