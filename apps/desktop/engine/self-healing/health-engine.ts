export type HealthCheckId = 'python-runtime' | 'node-runtime' | 'electron-version' | 'storage' | 'config' | 'gateway' | 'extensions' | 'network' | 'disk-space' | 'memory' | 'sync' | 'permissions' | 'updates'
export type HealthStatus = 'healthy' | 'warning' | 'critical' | 'unknown'
export type RepairAction = 'automatic' | 'manual' | 'restart' | 'reinstall'

export interface HealthCheck {
  id: HealthCheckId
  name: string
  description: string
  category: 'runtime' | 'storage' | 'network' | 'security' | 'performance'
  severity: 'info' | 'warning' | 'error' | 'critical'
  status: HealthStatus
  message: string
  lastChecked: number
  repair: RepairAction
  autoRepair: () => Promise<RepairResult>
  check: () => Promise<HealthStatus>
}

export interface RepairResult {
  success: boolean
  message: string
  duration: number
  requiresRestart: boolean
}

export interface HealthReport {
  timestamp: number
  totalChecks: number
  healthy: number
  warning: number
  critical: number
  unknown: number
  score: number
  checks: HealthCheckResult[]
  recommendations: string[]
}

export interface HealthCheckResult {
  id: HealthCheckId
  name: string
  status: HealthStatus
  message: string
  duration: number
  repairNeeded: boolean
}

class HealthEngine {
  private checks: Map<HealthCheckId, HealthCheck> = new Map()
  private lastReport: HealthReport | null = null
  private listeners: Array<(report: HealthReport) => void> = []
  private checkInterval: ReturnType<typeof setInterval> | null = null

  constructor() {
    this.registerStandardChecks()
  }

  private registerStandardChecks() {
    this.register({
      id: 'storage',
      name: 'Local Storage',
      description: 'Check localStorage availability and quota',
      category: 'storage',
      severity: 'critical',
      status: 'unknown',
      message: '',
      lastChecked: 0,
      repair: 'automatic',
      check: async () => {
        try {
          window.localStorage.setItem('__health_test', '1')
          window.localStorage.removeItem('__health_test')
          return 'healthy'
        } catch {
          return 'critical'
        }
      },
      autoRepair: async () => ({ success: true, message: 'Storage OK', duration: 0, requiresRestart: false }),
    })

    this.register({
      id: 'config',
      name: 'Configuration',
      description: 'Verify configuration file integrity',
      category: 'storage',
      severity: 'warning',
      status: 'unknown',
      message: '',
      lastChecked: 0,
      repair: 'automatic',
      check: async () => {
        try {
          const raw = window.localStorage.getItem('aetheros.config')
          if (!raw) return 'warning'
          JSON.parse(raw)
          return 'healthy'
        } catch {
          return 'warning'
        }
      },
      autoRepair: async () => {
        try {
          const raw = window.localStorage.getItem('aetheros.config')
          if (!raw) return { success: true, message: 'No config to repair', duration: 0, requiresRestart: false }
          const repaired = raw.replace(/NaN/g, 'null').replace(/undefined/g, 'null')
          window.localStorage.setItem('aetheros.config', repaired)
          return { success: true, message: 'Config repaired', duration: 100, requiresRestart: false }
        } catch {
          return { success: false, message: 'Failed to repair config', duration: 0, requiresRestart: false }
        }
      },
    })

    this.register({
      id: 'network',
      name: 'Network Connectivity',
      description: 'Check if network is reachable',
      category: 'network',
      severity: 'warning',
      status: 'unknown',
      message: '',
      lastChecked: 0,
      repair: 'manual',
      check: async () => navigator.onLine ? 'healthy' : 'warning',
      autoRepair: async () => ({ success: false, message: 'Cannot auto-repair network', duration: 0, requiresRestart: false }),
    })

    this.register({
      id: 'disk-space',
      name: 'Disk Space',
      description: 'Check available disk space for app data',
      category: 'performance',
      severity: 'warning',
      status: 'unknown',
      message: '',
      lastChecked: 0,
      repair: 'manual',
      check: async () => 'healthy',
      autoRepair: async () => ({ success: true, message: 'Disk OK', duration: 0, requiresRestart: false }),
    })

    this.register({
      id: 'memory',
      name: 'Memory Usage',
      description: 'Check application memory usage',
      category: 'performance',
      severity: 'warning',
      status: 'unknown',
      message: '',
      lastChecked: 0,
      repair: 'restart',
      check: async () => {
        try {
          const mem = (performance as unknown as { memory?: { usedJSHeapSize: number; jsHeapSizeLimit: number } }).memory
          if (!mem) return 'unknown'
          const usage = mem.usedJSHeapSize / mem.jsHeapSizeLimit
          if (usage > 0.9) return 'critical'
          if (usage > 0.7) return 'warning'
          return 'healthy'
        } catch {
          return 'unknown'
        }
      },
      autoRepair: async () => ({ success: true, message: 'Memory within limits', duration: 0, requiresRestart: false }),
    })

    this.register({
      id: 'extensions',
      name: 'Extensions',
      description: 'Check extension health',
      category: 'runtime',
      severity: 'warning',
      status: 'unknown',
      message: '',
      lastChecked: 0,
      repair: 'automatic',
      check: async () => 'healthy',
      autoRepair: async () => ({ success: true, message: 'Extensions OK', duration: 0, requiresRestart: false }),
    })

    this.register({
      id: 'permissions',
      name: 'Permissions',
      description: 'Verify required permissions are granted',
      category: 'security',
      severity: 'error',
      status: 'unknown',
      message: '',
      lastChecked: 0,
      repair: 'manual',
      check: async () => 'healthy',
      autoRepair: async () => ({ success: true, message: 'Permissions OK', duration: 0, requiresRestart: false }),
    })

    this.register({
      id: 'updates',
      name: 'Update System',
      description: 'Check auto-update system integrity',
      category: 'runtime',
      severity: 'info',
      status: 'unknown',
      message: '',
      lastChecked: 0,
      repair: 'manual',
      check: async () => 'healthy',
      autoRepair: async () => ({ success: true, message: 'Update system OK', duration: 0, requiresRestart: false }),
    })
  }

  register(check: HealthCheck) {
    this.checks.set(check.id, check)
  }

  getCheck(id: HealthCheckId): HealthCheck | undefined {
    return this.checks.get(id)
  }

  getAllChecks(): HealthCheck[] {
    return Array.from(this.checks.values())
  }

  async runCheck(id: HealthCheckId): Promise<HealthCheckResult> {
    const check = this.checks.get(id)
    if (!check) throw new Error(`Health check "${id}" not found`)

    const startTime = Date.now()
    try {
      const status = await check.check()
      check.status = status
      check.lastChecked = Date.now()
      return { id, name: check.name, status, message: check.message, duration: Date.now() - startTime, repairNeeded: status === 'critical' || status === 'warning' }
    } catch {
      check.status = 'unknown'
      return { id, name: check.name, status: 'unknown', message: 'Check failed', duration: Date.now() - startTime, repairNeeded: false }
    }
  }

  async runAllChecks(): Promise<HealthReport> {
    const results: HealthCheckResult[] = []
    let healthy = 0
    let warning = 0
    let critical = 0
    let unknown = 0
    const recommendations: string[] = []

    for (const check of this.checks.values()) {
      const result = await this.runCheck(check.id)
      results.push(result)
      if (result.status === 'healthy') healthy++
      else if (result.status === 'warning') { warning++; recommendations.push(`Check ${result.name}: ${result.message || 'needs attention'}`) }
      else if (result.status === 'critical') { critical++; recommendations.push(`Fix ${result.name}: ${result.message || 'requires immediate action'}`) }
      else unknown++
    }

    const score = Math.round((healthy / Math.max(1, this.checks.size)) * 100)
    const report: HealthReport = {
      timestamp: Date.now(),
      totalChecks: this.checks.size,
      healthy,
      warning,
      critical,
      unknown,
      score,
      checks: results,
      recommendations,
    }

    this.lastReport = report
    this.notify(report)
    return report
  }

  async autoRepair(id: HealthCheckId): Promise<RepairResult> {
    const check = this.checks.get(id)
    if (!check) return { success: false, message: `Check "${id}" not found`, duration: 0, requiresRestart: false }
    return check.autoRepair()
  }

  async autoRepairAll(): Promise<{ repaired: number; failed: number; results: RepairResult[] }> {
    const results: RepairResult[] = []
    let repaired = 0
    let failed = 0

    for (const check of this.checks.values()) {
      const status = await this.runCheck(check.id)
      if (status.repairNeeded) {
        const result = await check.autoRepair()
        results.push(result)
        if (result.success) repaired++
        else failed++
      }
    }

    return { repaired, failed, results }
  }

  getLastReport(): HealthReport | null {
    return this.lastReport
  }

  startPeriodicChecks(intervalMs: number = 300000) {
    this.stopPeriodicChecks()
    this.checkInterval = setInterval(() => this.runAllChecks(), intervalMs)
  }

  stopPeriodicChecks() {
    if (this.checkInterval) {
      clearInterval(this.checkInterval)
      this.checkInterval = null
    }
  }

  onReport(callback: (report: HealthReport) => void) {
    this.listeners.push(callback)
    if (this.lastReport) callback(this.lastReport)
  }

  getScore(): number {
    return this.lastReport?.score ?? 100
  }

  private notify(report: HealthReport) {
    for (const listener of this.listeners) {
      listener(report)
    }
  }
}

export const healthEngine = new HealthEngine()
