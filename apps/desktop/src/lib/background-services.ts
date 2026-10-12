import { syncEngineState, updateJarvisSystemStatus } from '@/store/jarvis-mode'
import { type HealthStatus, type SystemStats, updateHealthStatus, updateSystemStats } from '@/store/system'

let pollInterval: ReturnType<typeof setInterval> | null = null
const POLL_MS = 5000

export function startBackgroundServices() {
  if (pollInterval) {return}
  pollInterval = setInterval(pollSystemStats, POLL_MS)
  pollSystemStats()
}

export function stopBackgroundServices() {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
}

async function pollJarvisBackend() {
  // The legacy standalone Jarvis backend on :9789 no longer exists — the real
  // engine state arrives via the gateway socket + main-process health IPC.
  // Probing a dead port only produced ECONNREFUSED noise and a misleading
  // local-fallback init. Report through the real channels instead.
  try {
    if (window.aetherosDesktop?.getHealthStatus) {
      const health = await window.aetherosDesktop.getHealthStatus() as HealthStatus & {
        backend?: { reachable?: boolean }
      }

      const backendRunning =
        health.overall === 'healthy' || health.backend?.reachable === true ||
        health.services?.some(s => s.status === 'running')

      updateJarvisSystemStatus({ backend: backendRunning ? 'running' : 'stopped' })

      if (backendRunning) {
        syncEngineState({ phase: 'idle', cycleCount: 0, isRunning: true })
      }
    }
  } catch {
    // Non-fatal — the gateway sync owns the displayed state.
  }
}

async function pollSystemStats() {
  try {
    if (window.aetherosDesktop?.getSystemStats) {
      const stats: SystemStats = await window.aetherosDesktop.getSystemStats()
      updateSystemStats(stats)
    }
  } catch {
    // Non-fatal
  }

  try {
    if (window.aetherosDesktop?.getHealthStatus) {
      const health = await window.aetherosDesktop.getHealthStatus() as HealthStatus
      updateHealthStatus(health)
    }
  } catch {
    // Non-fatal
  }

  await pollJarvisBackend()
}

export async function restartPythonRuntime(): Promise<boolean> {
  try {
    if (window.aetherosDesktop?.restartBackend) {
      await window.aetherosDesktop.restartBackend()

      return true
    }
  } catch {
    // Non-fatal
  }

  return false
}

export async function getServiceLogs(serviceId: string): Promise<string[]> {
  try {
    if (window.aetherosDesktop?.getServiceLogs) {
      return await window.aetherosDesktop.getServiceLogs(serviceId)
    }
  } catch {
    // Non-fatal
  }

  return []
}
