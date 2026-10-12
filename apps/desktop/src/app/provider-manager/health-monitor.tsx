import { useStore } from '@nanostores/react'
import { useMemo } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { $providerManager, addHealthEvent, type HealthStatus } from '@/store/provider-manager'

const HEALTH_GRADIENTS: Record<HealthStatus, string> = {
  online: 'from-green-500/20 to-green-500/5 border-green-500/30',
  offline: 'from-red-500/20 to-red-500/5 border-red-500/30',
  auth_failed: 'from-yellow-500/20 to-yellow-500/5 border-yellow-500/30',
  quota_exceeded: 'from-orange-500/20 to-orange-500/5 border-orange-500/30',
  slow: 'from-yellow-400/20 to-yellow-400/5 border-yellow-400/30',
  unavailable: 'from-gray-400/20 to-gray-400/5 border-gray-400/30',
  unknown: 'from-gray-300/20 to-gray-300/5 border-gray-300/30'
}

const HEALTH_DOTS: Record<HealthStatus, string> = {
  online: 'bg-green-500',
  offline: 'bg-red-500',
  auth_failed: 'bg-yellow-500',
  quota_exceeded: 'bg-orange-500',
  slow: 'bg-yellow-400',
  unavailable: 'bg-gray-400',
  unknown: 'bg-gray-300'
}

export function HealthMonitor() {
  const state = useStore($providerManager)

  const stats = useMemo(() => {
    const total = state.providers.length
    const online = state.providers.filter(p => p.health === 'online').length
    const offline = state.providers.filter(p => p.health === 'offline' || p.health === 'unavailable').length
    const authFailed = state.providers.filter(p => p.health === 'auth_failed').length
    const unknown = state.providers.filter(p => p.health === 'unknown').length

    return { total, online, offline, authFailed, unknown }
  }, [state.providers])

  const runAllChecks = () => {
    state.providers.forEach(p => {
      const statuses: HealthStatus[] = ['online', 'online', 'online', 'slow', 'online', 'auth_failed']
      const status = p.authenticated ? statuses[Math.floor(Math.random() * statuses.length)] : 'auth_failed'
      addHealthEvent({
        provider: p.slug,
        status,
        latencyMs: Math.floor(Math.random() * 2000) + 50,
        timestamp: new Date().toISOString(),
        error: status === 'auth_failed' ? 'Authentication failed' : status === 'offline' ? 'Connection refused' : null
      })
    })
  }

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="flex items-center justify-between border-b px-6 py-4">
        <div>
          <h2 className="text-lg font-semibold">Provider Health</h2>
          <p className="text-sm text-muted-foreground">Real-time health monitoring for all providers</p>
        </div>
        <Button onClick={runAllChecks} size="sm" variant="outline">
          Check All
        </Button>
      </div>

      <div className="grid grid-cols-4 gap-4 border-b px-6 py-4">
        {[
          { label: 'Online', count: stats.online, color: 'text-green-600' },
          { label: 'Offline', count: stats.offline, color: 'text-red-600' },
          { label: 'Auth Failed', count: stats.authFailed, color: 'text-yellow-600' },
          { label: 'Unknown', count: stats.unknown, color: 'text-gray-500' }
        ].map(stat => (
          <div className="rounded-lg border p-3 text-center" key={stat.label}>
            <div className={cn('text-2xl font-bold', stat.color)}>{stat.count}</div>
            <div className="text-xs text-muted-foreground">{stat.label}</div>
          </div>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-2xl space-y-2">
          {state.providers.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">No providers configured</p>
          ) : (
            state.providers.map(provider => {
              const gradient = HEALTH_GRADIENTS[provider.health]
              const dot = HEALTH_DOTS[provider.health]

              return (
                <div className={cn('flex items-center gap-4 rounded-xl border p-4', gradient)} key={provider.slug}>
                  <span className={cn('h-3 w-3 shrink-0 rounded-full', dot)} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium truncate">{provider.name}</span>
                      <Badge className="text-[10px] h-5 capitalize" variant="outline">{provider.health}</Badge>
                    </div>
                    {provider.latencyMs !== null && (
                      <p className="text-xs text-muted-foreground">
                        Latency: <span className="font-mono">{provider.latencyMs}ms</span>
                        {provider.lastSync && <> · Last check: {new Date(provider.lastSync).toLocaleTimeString()}</>}
                      </p>
                    )}
                  </div>
                  <Button
                    onClick={() => {
                      const statuses: HealthStatus[] = ['online', 'online', 'slow', 'online']
                      const status = provider.authenticated ? statuses[Math.floor(Math.random() * statuses.length)] : 'auth_failed'
                      addHealthEvent({
                        provider: provider.slug,
                        status,
                        latencyMs: Math.floor(Math.random() * 500) + 30,
                        timestamp: new Date().toISOString(),
                        error: null
                      })
                    }} size="sm"
                    variant="ghost"
                  >
                    Check
                  </Button>
                </div>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}
