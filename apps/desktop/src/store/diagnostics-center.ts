import { atom } from 'nanostores'

export type CheckSeverity = 'info' | 'warning' | 'error'
export type CheckCategory = 'system' | 'network' | 'storage' | 'plugins' | 'security' | 'performance'
export type RepairStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface DiagnosticCheck {
  id: string
  name: string
  description: string
  category: CheckCategory
  severity: CheckSeverity
  status: 'pending' | 'running' | 'passed' | 'failed' | 'warning'
  message?: string
  duration?: number
}

export interface RepairAction {
  id: string
  checkId: string
  name: string
  description: string
  status: RepairStatus
  requiresRestart: boolean
  output?: string
}

export interface HealthReport {
  id: string
  timestamp: number
  score: number
  checks: DiagnosticCheck[]
  summary: string
}

export interface DiagnosticsState {
  checks: DiagnosticCheck[]
  repairs: RepairAction[]
  reports: HealthReport[]
  runningAll: boolean
  selectedCategory: CheckCategory | 'all'
}

const DEFAULT_CHECKS: DiagnosticCheck[] = [
  { id: 'sys-cpu', name: 'CPU Health', description: 'Check CPU temperature and load', category: 'system', severity: 'warning', status: 'pending' },
  { id: 'sys-memory', name: 'Memory Integrity', description: 'Verify RAM availability and swap usage', category: 'system', severity: 'warning', status: 'pending' },
  { id: 'sys-uptime', name: 'System Uptime', description: 'Check system uptime and stability', category: 'system', severity: 'info', status: 'pending' },
  { id: 'net-connectivity', name: 'Network Connectivity', description: 'Verify internet and gateway connectivity', category: 'network', severity: 'error', status: 'pending' },
  { id: 'net-dns', name: 'DNS Resolution', description: 'Check DNS resolution for API endpoints', category: 'network', severity: 'warning', status: 'pending' },
  { id: 'net-latency', name: 'API Latency', description: 'Measure latency to configured API endpoints', category: 'network', severity: 'info', status: 'pending' },
  { id: 'st-capacity', name: 'Disk Capacity', description: 'Check available disk space', category: 'storage', severity: 'warning', status: 'pending' },
  { id: 'st-permissions', name: 'File Permissions', description: 'Verify config and data directory permissions', category: 'storage', severity: 'error', status: 'pending' },
  { id: 'st-config', name: 'Config Integrity', description: 'Validate config.yaml structure', category: 'storage', severity: 'warning', status: 'pending' },
  { id: 'pl-compatibility', name: 'Plugin Compatibility', description: 'Check installed plugin versions', category: 'plugins', severity: 'warning', status: 'pending' },
  { id: 'pl-dependencies', name: 'Plugin Dependencies', description: 'Verify plugin dependency resolution', category: 'plugins', severity: 'error', status: 'pending' },
  { id: 'pl-hooks', name: 'Hook Registration', description: 'Validate plugin hook registrations', category: 'plugins', severity: 'info', status: 'pending' },
  { id: 'sec-keys', name: 'API Key Validation', description: 'Check configured API keys format', category: 'security', severity: 'warning', status: 'pending' },
  { id: 'sec-env', name: 'Environment Audit', description: 'Audit environment variable security', category: 'security', severity: 'warning', status: 'pending' },
  { id: 'sec-permissions', name: 'Permission Audit', description: 'Review permission configurations', category: 'security', severity: 'info', status: 'pending' },
  { id: 'perf-cache', name: 'Cache Efficiency', description: 'Analyze prompt cache hit rates', category: 'performance', severity: 'info', status: 'pending' },
  { id: 'perf-loop', name: 'Agent Loop Health', description: 'Check for agent loop inefficiencies', category: 'performance', severity: 'warning', status: 'pending' },
  { id: 'perf-memory', name: 'Memory Leak Detection', description: 'Detect potential memory leaks', category: 'performance', severity: 'error', status: 'pending' }
]

const DEFAULT_REPAIRS: RepairAction[] = [
  { id: 'rep-clear-cache', checkId: 'perf-cache', name: 'Clear Prompt Cache', description: 'Reset the prompt cache to eliminate stale entries', status: 'pending', requiresRestart: false },
  { id: 'rep-restart-gateway', checkId: 'net-connectivity', name: 'Restart Gateway', description: 'Restart the gateway service to re-establish connections', status: 'pending', requiresRestart: false },
  { id: 'rep-validate-config', checkId: 'st-config', name: 'Validate & Repair Config', description: 'Parse config.yaml and fix common issues', status: 'pending', requiresRestart: true },
  { id: 'rep-reindex-plugins', checkId: 'pl-compatibility', name: 'Reindex Plugins', description: 'Force re-scan of installed plugins', status: 'pending', requiresRestart: false },
  { id: 'rep-clean-temp', checkId: 'st-capacity', name: 'Clean Temp Files', description: 'Remove temporary and cache files to free space', status: 'pending', requiresRestart: false },
  { id: 'rep-reset-network', checkId: 'net-dns', name: 'Reset Network Stack', description: 'Clear DNS cache and reset network connections', status: 'pending', requiresRestart: false }
]

export const $diagnostics = atom<DiagnosticsState>({
  checks: DEFAULT_CHECKS,
  repairs: DEFAULT_REPAIRS,
  reports: [],
  runningAll: false,
  selectedCategory: 'all'
})

const patch = (u: Partial<DiagnosticsState>) =>
  $diagnostics.set({ ...$diagnostics.get(), ...u })

export function setDiagnosticCategory(c: CheckCategory | 'all') { patch({ selectedCategory: c }) }

export function updateCheck(id: string, update: Partial<DiagnosticCheck>) {
  const checks = $diagnostics.get().checks.map(c => c.id === id ? { ...c, ...update } : c)
  patch({ checks })
}

export function updateRepair(id: string, update: Partial<RepairAction>) {
  const repairs = $diagnostics.get().repairs.map(r => r.id === id ? { ...r, ...update } : r)
  patch({ repairs })
}

export function addReport(report: HealthReport) {
  patch({ reports: [...$diagnostics.get().reports.slice(-19), report] })
}

export function setRunningAll(v: boolean) { patch({ runningAll: v }) }

export function resetChecks() {
  patch({ checks: DEFAULT_CHECKS.map(c => ({ ...c, status: 'pending' as const })) })
}

export function resetRepairs() {
  patch({ repairs: DEFAULT_REPAIRS.map(r => ({ ...r, status: 'pending' as const })) })
}
