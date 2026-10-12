import { atom } from 'nanostores'

export interface SystemStats {
  cpu: number
  memory: { used: number; total: number; percent: number }
  gpu?: { used: number; total: number; percent: number; name: string }
  platform: string
  hostname: string
  uptime: number
}

export interface ServiceStatus {
  id: string
  name: string
  status: 'running' | 'stopped' | 'error'
  uptime?: number
  memory?: number
  error?: string
}

export interface HealthStatus {
  overall: 'healthy' | 'degraded' | 'unhealthy'
  services: ServiceStatus[]
  lastCheck: number
}

export const $systemStats = atom<SystemStats | null>(null)
export const $healthStatus = atom<HealthStatus | null>(null)
export const $tokenUsage = atom<{ input: number; output: number; total: number }>({ input: 0, output: 0, total: 0 })
export const $backgroundTaskCount = atom(0)
export const $syncStatus = atom<'idle' | 'syncing' | 'error'>('idle')
export const $securityStatus = atom<'secure' | 'warning' | 'critical'>('secure')

export function updateSystemStats(stats: SystemStats) {
  $systemStats.set(stats)
}

export function updateHealthStatus(health: HealthStatus) {
  $healthStatus.set(health)
}

export function updateTokenUsage(input: number, output: number) {
  $tokenUsage.set({ input, output, total: input + output })
}

export function setBackgroundTaskCount(count: number) {
  $backgroundTaskCount.set(count)
}

export function setSyncStatus(status: 'idle' | 'syncing' | 'error') {
  $syncStatus.set(status)
}

export function setSecurityStatus(status: 'secure' | 'warning' | 'critical') {
  $securityStatus.set(status)
}
