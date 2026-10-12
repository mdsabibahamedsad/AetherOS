export interface PerformanceSnapshot {
  timestamp: number
  startup: StartupMetrics
  cpu: CPUMetrics
  gpu: GPUMetrics
  memory: MemoryMetrics
  disk: DiskMetrics
  extensions: ExtensionMetrics
  models: ModelMetrics
  automation: AutomationMetrics
}

export interface StartupMetrics {
  coldStart: number
  warmStart: number
  mainProcessInit: number
  preloadExec: number
  firstPaint: number
  timeToInteractive: number
}

export interface CPUMetrics {
  overall: number
  process: number
  system: number
  cores: number
}

export interface GPUMetrics {
  usage: number
  memoryUsed: number
  memoryTotal: number
  temperature?: number
}

export interface MemoryMetrics {
  heapUsed: number
  heapTotal: number
  systemUsed: number
  systemTotal: number
  process: number
}

export interface DiskMetrics {
  readSpeed: number
  writeSpeed: number
  usage: number
  total: number
}

export interface ExtensionMetrics {
  loaded: number
  active: number
  failed: number
  memoryUsage: number
}

export interface ModelMetrics {
  loaded: number
  activeInferences: number
  averageLatency: number
  cacheHitRate: number
}

export interface AutomationMetrics {
  activeWorkflows: number
  completedToday: number
  failedToday: number
  averageDuration: number
}

const SNAPSHOT_HISTORY_KEY = 'aetheros.performance.history'
const MAX_HISTORY = 1000

class PerformanceMonitor {
  private history: PerformanceSnapshot[] = []
  private listeners: Array<(snapshot: PerformanceSnapshot) => void> = []
  private intervalId: ReturnType<typeof setInterval> | null = null
  private collectionInterval = 60000
  private isCollecting = false

  constructor() {
    this.loadHistory()
  }

  startCollection(intervalMs: number = 60000) {
    this.collectionInterval = intervalMs
    if (this.intervalId) return

    this.collectSnapshot()
    this.intervalId = setInterval(() => this.collectSnapshot(), this.collectionInterval)
  }

  stopCollection() {
    if (this.intervalId) {
      clearInterval(this.intervalId)
      this.intervalId = null
    }
  }

  async collectSnapshot(): Promise<PerformanceSnapshot> {
    const snapshot: PerformanceSnapshot = {
      timestamp: Date.now(),
      startup: this.collectStartupMetrics(),
      cpu: await this.collectCPUMetrics(),
      gpu: await this.collectGPUMetrics(),
      memory: await this.collectMemoryMetrics(),
      disk: await this.collectDiskMetrics(),
      extensions: this.collectExtensionMetrics(),
      models: this.collectModelMetrics(),
      automation: this.collectAutomationMetrics(),
    }

    this.history.push(snapshot)
    if (this.history.length > MAX_HISTORY) {
      this.history = this.history.slice(-MAX_HISTORY)
    }

    this.saveHistory()
    this.notify(snapshot)
    return snapshot
  }

  getHistory(): PerformanceSnapshot[] {
    return [...this.history]
  }

  getRecentSnapshots(count: number = 10): PerformanceSnapshot[] {
    return this.history.slice(-count)
  }

  getSnapshotsInRange(from: number, to: number): PerformanceSnapshot[] {
    return this.history.filter(s => s.timestamp >= from && s.timestamp <= to)
  }

  getAverages(): Partial<PerformanceSnapshot> {
    if (this.history.length === 0) return {}

    const avg = <T extends keyof PerformanceSnapshot>(key: T): number => {
      const values = this.history.map(s => {
        const val = s[key]
        if (typeof val === 'object' && val !== null) {
          const numeric = Object.values(val as unknown as Record<string, unknown>).filter(v => typeof v === 'number') as number[]
          return numeric.reduce((a, b) => a + b, 0) / numeric.length
        }
        return 0
      })
      return values.reduce((a, b) => a + b, 0) / values.length
    }

    return {
      timestamp: Date.now(),
      cpu: { overall: avg('cpu'), process: 0, system: 0, cores: 0 },
      memory: { heapUsed: avg('memory'), heapTotal: 0, systemUsed: 0, systemTotal: 0, process: 0 },
    } as PerformanceSnapshot
  }

  getLatest(): PerformanceSnapshot | null {
    return this.history.length > 0 ? this.history[this.history.length - 1] : null
  }

  clearHistory() {
    this.history = []
    this.saveHistory()
  }

  onChange(callback: (snapshot: PerformanceSnapshot) => void) {
    this.listeners.push(callback)
  }

  isCollectingStatus(): boolean {
    return this.isCollecting
  }

  private collectStartupMetrics(): StartupMetrics {
    const nav = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming | undefined
    return {
      coldStart: nav ? nav.domContentLoadedEventEnd : 0,
      warmStart: 0,
      mainProcessInit: 0,
      preloadExec: 0,
      firstPaint: getFirstPaint(),
      timeToInteractive: nav ? nav.domComplete : 0,
    }
  }

  private async collectCPUMetrics(): Promise<CPUMetrics> {
    return {
      overall: await getCPUUsage(),
      process: 0,
      system: 0,
      cores: navigator.hardwareConcurrency || 0,
    }
  }

  private async collectGPUMetrics(): Promise<GPUMetrics> {
    return { usage: 0, memoryUsed: 0, memoryTotal: 0 }
  }

  private async collectMemoryMetrics(): Promise<MemoryMetrics> {
    if ((performance as unknown as { memory?: { usedJSHeapSize: number; totalJSHeapSize: number; jsHeapSizeLimit: number } }).memory) {
      const mem = (performance as unknown as { memory: { usedJSHeapSize: number; totalJSHeapSize: number; jsHeapSizeLimit: number } }).memory
      return {
        heapUsed: mem.usedJSHeapSize,
        heapTotal: mem.totalJSHeapSize,
        systemUsed: mem.usedJSHeapSize,
        systemTotal: mem.jsHeapSizeLimit,
        process: 0,
      }
    }
    return { heapUsed: 0, heapTotal: 0, systemUsed: 0, systemTotal: 0, process: 0 }
  }

  private async collectDiskMetrics(): Promise<DiskMetrics> {
    return { readSpeed: 0, writeSpeed: 0, usage: 0, total: 0 }
  }

  private collectExtensionMetrics(): ExtensionMetrics {
    return { loaded: 0, active: 0, failed: 0, memoryUsage: 0 }
  }

  private collectModelMetrics(): ModelMetrics {
    return { loaded: 0, activeInferences: 0, averageLatency: 0, cacheHitRate: 0 }
  }

  private collectAutomationMetrics(): AutomationMetrics {
    return { activeWorkflows: 0, completedToday: 0, failedToday: 0, averageDuration: 0 }
  }

  private notify(snapshot: PerformanceSnapshot) {
    for (const listener of this.listeners) {
      listener(snapshot)
    }
  }

  private loadHistory() {
    try {
      const raw = window.localStorage.getItem(SNAPSHOT_HISTORY_KEY)
      if (raw) {
        this.history = JSON.parse(raw)
      }
    } catch {
      this.history = []
    }
  }

  private saveHistory() {
    try {
      if (this.history.length > 0) {
        window.localStorage.setItem(SNAPSHOT_HISTORY_KEY, JSON.stringify(this.history.slice(-100)))
      }
    } catch {
      console.error('Failed to save performance history')
    }
  }
}

function getFirstPaint(): number {
  const entries = performance.getEntriesByType('paint')
  const fcp = entries.find(e => e.name === 'first-contentful-paint')
  return fcp ? fcp.startTime : 0
}

async function getCPUUsage(): Promise<number> {
  if ('requestIdleCallback' in window) {
    return new Promise((resolve) => {
      const start = performance.now()
      requestIdleCallback(() => {
        const elapsed = performance.now() - start
        resolve(Math.min(elapsed / 50, 1))
      })
    })
  }
  return 0
}

export const performanceMonitor = new PerformanceMonitor()
