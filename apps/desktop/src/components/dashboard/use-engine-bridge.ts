import { useEffect } from 'react'

import { addActivityEvent, setBackupState, setDashboardMetrics, setHealthChecks, setRuntimeStatus } from '@/store/dashboard'
import { updateHealthStatus } from '@/store/system'

import { backupEngine } from '../../../engine/backup/backup-engine'
import { runtimeManager } from '../../../engine/installer/runtime-manager'
import { type DashboardData, performanceDashboardStore } from '../../../engine/performance/dashboard-store'
import { healthEngine } from '../../../engine/self-healing/health-engine'
import { repairSystem } from '../../../engine/self-healing/repair-system'

export function useEngineBridge() {
  useEffect(() => {
    if (typeof window === 'undefined') {return}

    healthEngine.onReport(report => {
      setHealthChecks(
        report.checks.map(c => ({
          id: c.id,
          name: c.name,
          status: c.status === 'healthy' ? 'passed' : c.status === 'warning' ? 'warning' : 'failed',
          message: c.message || statusMessage(c.status),
          lastChecked: report.timestamp
        }))
      )
      updateHealthStatus({
        overall: report.score >= 80 ? 'healthy' : report.score >= 50 ? 'degraded' : 'unhealthy',
        services: [],
        lastCheck: report.timestamp
      })
    })

    const runtimes = runtimeManager.getRequirements()
    runtimeManager.checkAllRuntimes().then(() => {
      const updated = runtimeManager.getRequirements()
      setRuntimeStatus({
        node: { installed: updated.find(r => r.type === 'node')?.status === 'installed' || false, version: updated.find(r => r.type === 'node')?.currentVersion || '', path: '' },
        python: { installed: updated.find(r => r.type === 'python')?.status === 'installed' || false, version: updated.find(r => r.type === 'python')?.currentVersion || '', path: '' },
        git: { installed: updated.find(r => r.type === 'git')?.status === 'installed' || false, version: updated.find(r => r.type === 'git')?.currentVersion || '', path: '' },
        dependencies: { installed: true, count: 0 }
      })
    })

    const backupConfig = backupEngine.getConfig()
    const backups = backupEngine.getBackups()
    setBackupState({
      lastBackup: backups.length > 0 ? backups[0].date.getTime() : null,
      nextBackup: backupConfig.autoBackup ? Date.now() + scheduleMs(backupConfig.schedule) : null,
      schedule: backupConfig.schedule,
      status: 'idle',
      totalSize: formatTotalSize(backups),
      location: 'Local Storage',
      error: undefined
    })

    performanceDashboardStore.onChange((data: DashboardData) => {
      if (data.current) {
        const memPercent = data.current.memory.heapTotal > 0 ? (data.current.memory.heapUsed / data.current.memory.heapTotal) * 100 : 0
        setDashboardMetrics({
          cpu: { current: data.current.cpu.overall, average: (data.averages as any)?.cpu?.overall ?? data.current.cpu.overall, history: [data.current.cpu.overall] },
          memory: { used: data.current.memory.heapUsed, total: data.current.memory.heapTotal, percent: memPercent, history: [memPercent] },
          disk: { used: data.current.disk.usage, total: data.current.disk.total, percent: data.current.disk.total > 0 ? (data.current.disk.usage / data.current.disk.total) * 100 : 0 },
          uptime: data.uptime,
          sessions: { active: 0, total: 0 }
        })
      }
    })

    healthEngine.runAllChecks().then(report => {
      if (report.critical > 0) {
        addActivityEvent({
          id: `health-critical-${Date.now()}`, type: 'health', message: `${report.critical} critical health issue(s) detected`, timestamp: Date.now(), status: 'error'
        })
      }

      if (report.warning > 0) {
        addActivityEvent({
          id: `health-warning-${Date.now()}`, type: 'health', message: `${report.warning} health warning(s) found`, timestamp: Date.now(), status: 'warning'
        })
      }

      if (report.score === 100) {
        addActivityEvent({
          id: `health-pass-${Date.now()}`, type: 'health', message: 'All health checks passed', timestamp: Date.now(), status: 'success'
        })
      }
    })

    repairSystem.getHistory().forEach(h => {
      addActivityEvent({
        id: `repair-${h.timestamp}`, type: 'system', message: `Repair "${h.actionId}": ${h.success ? 'succeeded' : 'failed'}`, timestamp: h.timestamp, status: h.success ? 'success' : 'error'
      })
    })
  }, [])
}

function statusMessage(status: string): string {
  switch (status) {
    case 'healthy': return 'Check passed'

    case 'warning': return 'Needs attention'

    case 'critical': return 'Requires immediate action'

    default: return 'Status unknown'
  }
}

function scheduleMs(schedule: string): number {
  switch (schedule) {
    case 'hourly': return 3600000

    case 'daily': return 86400000

    case 'weekly': return 604800000

    default: return 86400000
  }
}

function formatTotalSize(backups: Array<{ size?: number }>): string {
  const total = backups.reduce((s, b) => s + (b.size ?? 0), 0)

  if (total === 0) {return '0 B'}
  const units = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(total) / Math.log(1024))

  return `${(total / Math.pow(1024, i)).toFixed(1)} ${units[i]}`
}
