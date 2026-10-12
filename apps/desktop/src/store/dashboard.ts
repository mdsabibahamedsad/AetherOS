import { atom } from 'nanostores'

export interface DashboardMetrics {
  cpu: { current: number; average: number; history: number[] }
  memory: { used: number; total: number; percent: number; history: number[] }
  disk: { used: number; total: number; percent: number }
  uptime: number
  sessions: { active: number; total: number }
}

export interface BackupState {
  lastBackup: number | null
  nextBackup: number | null
  schedule: string
  status: 'idle' | 'running' | 'success' | 'error'
  totalSize: string
  location: string
  error?: string
}

export interface HealthCheckResult {
  id: string
  name: string
  status: 'passed' | 'warning' | 'failed'
  message: string
  lastChecked: number
}

export interface RuntimeStatus {
  node: { installed: boolean; version: string; path: string }
  python: { installed: boolean; version: string; path: string }
  git: { installed: boolean; version: string; path: string }
  dependencies: { installed: boolean; count: number }
}

export interface ActivityEvent {
  id: string
  type: 'backup' | 'update' | 'health' | 'install' | 'system'
  message: string
  timestamp: number
  status: 'info' | 'success' | 'warning' | 'error'
}

export type DashboardView = 'overview' | 'health' | 'backup' | 'runtime'

export const $dashboardMetrics = atom<DashboardMetrics | null>(null)
export const $backupState = atom<BackupState>({
  lastBackup: null,
  nextBackup: null,
  schedule: 'daily',
  status: 'idle',
  totalSize: '0 B',
  location: ''
})
export const $healthChecks = atom<HealthCheckResult[]>([])
export const $runtimeStatus = atom<RuntimeStatus | null>(null)
export const $activityFeed = atom<ActivityEvent[]>([])
export const $dashboardView = atom<DashboardView>('overview')

export function setDashboardMetrics(metrics: DashboardMetrics) {
  $dashboardMetrics.set(metrics)
}

export function setBackupState(state: Partial<BackupState>) {
  $backupState.set({ ...$backupState.get(), ...state })
}

export function setHealthChecks(checks: HealthCheckResult[]) {
  $healthChecks.set(checks)
}

export function setRuntimeStatus(status: RuntimeStatus) {
  $runtimeStatus.set(status)
}

export function addActivityEvent(event: ActivityEvent) {
  const feed = $activityFeed.get()
  $activityFeed.set([event, ...feed].slice(0, 50))
}

export function setDashboardView(view: DashboardView) {
  $dashboardView.set(view)
}

export function simulateDashboardData() {
  setDashboardMetrics({
    cpu: { current: 34, average: 28, history: [22, 31, 45, 38, 29, 34, 41, 36, 30, 27, 33, 34] },
    memory: { used: 6.2, total: 16, percent: 38.75, history: [35, 37, 40, 38, 36, 39] },
    disk: { used: 234, total: 512, percent: 45.7 },
    uptime: Date.now() - 86400000 * 3,
    sessions: { active: 2, total: 24 }
  })

  setBackupState({
    lastBackup: Date.now() - 43200000,
    nextBackup: Date.now() + 43200000,
    schedule: 'daily',
    status: 'success',
    totalSize: '1.2 GB',
    location: 'C:\\Users\\User\\.aetheros\\backups'
  })

  setHealthChecks([
    { id: 'storage', name: 'Storage Integrity', status: 'passed', message: 'All stores consistent', lastChecked: Date.now() - 30000 },
    { id: 'config', name: 'Configuration', status: 'passed', message: 'Config valid, no corruption', lastChecked: Date.now() - 60000 },
    { id: 'network', name: 'Network Connectivity', status: 'warning', message: 'High latency on fallback route', lastChecked: Date.now() - 120000 },
    { id: 'disk', name: 'Disk Space', status: 'passed', message: '234 GB used of 512 GB', lastChecked: Date.now() - 300000 },
    { id: 'memory', name: 'Memory Pressure', status: 'passed', message: '6.2 GB / 16 GB used', lastChecked: Date.now() - 60000 },
    { id: 'extensions', name: 'Extensions Integrity', status: 'passed', message: 'All extensions validated', lastChecked: Date.now() - 120000 },
    { id: 'permissions', name: 'Permissions', status: 'passed', message: 'All file permissions correct', lastChecked: Date.now() - 180000 },
    { id: 'updates', name: 'Update Status', status: 'failed', message: 'Auto-update check failed — service unreachable', lastChecked: Date.now() - 600000 }
  ])

  setRuntimeStatus({
    node: { installed: true, version: '22.14.0', path: 'C:\\Program Files\\nodejs\\node.exe' },
    python: { installed: true, version: '3.12.9', path: 'C:\\Python312\\python.exe' },
    git: { installed: true, version: '2.48.1', path: 'C:\\Program Files\\Git\\bin\\git.exe' },
    dependencies: { installed: true, count: 847 }
  })
}
