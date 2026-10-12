import { performanceMonitor, type PerformanceSnapshot } from './performance-monitor'

export interface DashboardData {
  current: PerformanceSnapshot | null
  history: PerformanceSnapshot[]
  averages: Partial<PerformanceSnapshot>
  uptime: number
  status: 'collecting' | 'paused' | 'stopped'
  lastUpdate: number | null
}

class PerformanceDashboardStore {
  private data: DashboardData = {
    current: null,
    history: [],
    averages: {},
    uptime: 0,
    status: 'stopped',
    lastUpdate: null,
  }

  private listeners: Array<(data: DashboardData) => void> = []
  private appStartTime = Date.now()

  constructor() {
    performanceMonitor.onChange((snapshot) => {
      this.data.current = snapshot
      this.data.history = performanceMonitor.getRecentSnapshots(100)
      this.data.averages = performanceMonitor.getAverages()
      this.data.uptime = Math.floor((Date.now() - this.appStartTime) / 1000)
      this.data.lastUpdate = snapshot.timestamp
      this.notify()
    })
  }

  startMonitoring() {
    performanceMonitor.startCollection()
    this.data.status = 'collecting'
    this.notify()
  }

  stopMonitoring() {
    performanceMonitor.stopCollection()
    this.data.status = 'stopped'
    this.notify()
  }

  pauseMonitoring() {
    performanceMonitor.stopCollection()
    this.data.status = 'paused'
    this.notify()
  }

  getData(): DashboardData {
    return { ...this.data }
  }

  getCPUHistory(): { timestamp: number; value: number }[] {
    return this.data.history.map(s => ({
      timestamp: s.timestamp,
      value: s.cpu.overall,
    }))
  }

  getMemoryHistory(): { timestamp: number; heap: number; system: number }[] {
    return this.data.history.map(s => ({
      timestamp: s.timestamp,
      heap: s.memory.heapUsed,
      system: s.memory.systemUsed,
    }))
  }

  getStartupTimeline(): { label: string; value: number }[] {
    const current = this.data.current
    if (!current) return []
    return [
      { label: 'Cold Start', value: current.startup.coldStart },
      { label: 'First Paint', value: current.startup.firstPaint },
      { label: 'Time to Interactive', value: current.startup.timeToInteractive },
    ]
  }

  onChange(callback: (data: DashboardData) => void) {
    this.listeners.push(callback)
    callback({ ...this.data })
  }

  private notify() {
    for (const listener of this.listeners) {
      listener({ ...this.data })
    }
  }
}

export const performanceDashboardStore = new PerformanceDashboardStore()
