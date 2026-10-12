import { addJarvisNotification } from '@/store/jarvis-mode'
import type { JarvisSystemStatus } from '@/store/jarvis-mode'

// ─── Health Monitor ───────────────────────────────────────────────────────────

export interface HealthCheck {
  id: string
  name: string
  status: 'healthy' | 'degraded' | 'down'
  lastCheck: number
  latency: number
  error?: string
}

export interface SystemHealth {
  overall: 'healthy' | 'degraded' | 'critical'
  checks: HealthCheck[]
  lastFullCheck: number
  uptime: number
  recoveryAttempts: number
}

const healthChecks = new Map<string, HealthCheck>()

let systemHealth: SystemHealth = {
  overall: 'healthy',
  checks: [],
  lastFullCheck: Date.now(),
  uptime: Date.now(),
  recoveryAttempts: 0
}

// ─── Register Health Checks ───────────────────────────────────────────────────

export function registerHealthCheck(id: string, name: string) {
  healthChecks.set(id, {
    id,
    name,
    status: 'healthy',
    lastCheck: Date.now(),
    latency: 0
  })
}

export function updateHealthCheck(id: string, status: HealthCheck['status'], latency?: number, error?: string) {
  const check = healthChecks.get(id)

  if (!check) {return}

  check.status = status
  check.lastCheck = Date.now()

  if (latency !== undefined) {check.latency = latency}

  if (error) {check.error = error}

  // Auto-recovery
  if (status === 'down') {
    attemptRecovery(id)
  }
}

// ─── Auto-Recovery ────────────────────────────────────────────────────────────

const recoveryHandlers = new Map<string, () => Promise<boolean>>()

export function registerRecoveryHandler(id: string, handler: () => Promise<boolean>) {
  recoveryHandlers.set(id, handler)
}

async function attemptRecovery(id: string) {
  const handler = recoveryHandlers.get(id)

  if (!handler) {return}

  systemHealth.recoveryAttempts++
  addJarvisNotification({
    title: 'Auto-Recovery',
    message: `Attempting to recover ${id}...`,
    type: 'warning'
  })

  try {
    const success = await handler()

    if (success) {
      updateHealthCheck(id, 'healthy')
      addJarvisNotification({
        title: 'Recovery Successful',
        message: `${id} has been restored`,
        type: 'success'
      })
    } else {
      addJarvisNotification({
        title: 'Recovery Failed',
        message: `${id} could not be recovered automatically`,
        type: 'error'
      })
    }
  } catch (err) {
    addJarvisNotification({
      title: 'Recovery Error',
      message: `Recovery for ${id} failed: ${err}`,
      type: 'error'
    })
  }
}

// ─── System Health Assessment ─────────────────────────────────────────────────

export function assessSystemHealth(): SystemHealth {
  const checks = Array.from(healthChecks.values())
  const downCount = checks.filter(c => c.status === 'down').length
  const degradedCount = checks.filter(c => c.status === 'degraded').length

  let overall: SystemHealth['overall'] = 'healthy'

  if (downCount > 0) {overall = 'critical'}
  else if (degradedCount > 1) {overall = 'degraded'}

  systemHealth = {
    overall,
    checks,
    lastFullCheck: Date.now(),
    uptime: Date.now() - systemHealth.uptime,
    recoveryAttempts: systemHealth.recoveryAttempts
  }

  return systemHealth
}

export function getSystemHealth(): SystemHealth {
  return systemHealth
}

export function getHealthCheck(id: string): HealthCheck | undefined {
  return healthChecks.get(id)
}

export function getAllHealthChecks(): HealthCheck[] {
  return Array.from(healthChecks.values())
}

// ─── System Status Fetcher ────────────────────────────────────────────────────

export async function fetchSystemStatus(): Promise<Partial<JarvisSystemStatus>> {
  const status: Partial<JarvisSystemStatus> = {}

  try {
    const stats = await window.aetherosDesktop?.getSystemStats?.()

    if (stats) {
      status.cpu = stats.cpu
      status.memory = stats.memory
      status.gpu = stats.gpu
      status.uptime = stats.uptime
    }
  } catch { /* ignore */ }

  try {
    const health = await window.aetherosDesktop?.getHealthStatus?.()

    if (health) {
      status.backend = health.overall === 'healthy' ? 'running' : 'stopped'
    }
  } catch { /* ignore */ }

  return status
}

// ─── Initialize ───────────────────────────────────────────────────────────────

export function initializeMonitoring() {
  registerHealthCheck('python-runtime', 'Python Runtime')
  registerHealthCheck('gateway', 'Gateway Connection')
  registerHealthCheck('mcp', 'MCP Servers')
  registerHealthCheck('agents', 'Agent System')
  registerHealthCheck('memory', 'Memory System')
  registerHealthCheck('scheduler', 'Scheduler')
}
