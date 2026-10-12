import { useStore } from '@nanostores/react'
import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

import { ActivityFeed } from '@/components/dashboard/activity-feed'
import { AutoRepairPanel } from '@/components/dashboard/auto-repair-panel'
import { BackupPanel } from '@/components/dashboard/backup-panel'
import { HealthStatus } from '@/components/dashboard/health-status'
import { RuntimePanel } from '@/components/dashboard/runtime-panel'
import { StatsCard } from '@/components/dashboard/stats-card'
import { SystemMetrics } from '@/components/dashboard/system-metrics'
import { useEngineBridge } from '@/components/dashboard/use-engine-bridge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'
import { $dashboardMetrics, $dashboardView, addActivityEvent, setDashboardView, simulateDashboardData } from '@/store/dashboard'
import { $healthStatus, $securityStatus, $syncStatus, $systemStats, $tokenUsage } from '@/store/system'

const TABS = [
  { id: 'overview' as const, label: 'Overview' },
  { id: 'health' as const, label: 'Health' },
  { id: 'backup' as const, label: 'Backup' },
  { id: 'runtime' as const, label: 'Runtime' }
]

export function DashboardView() {
  const navigate = useNavigate()
  const view = useStore($dashboardView)
  const stats = useStore($systemStats)
  const health = useStore($healthStatus)
  const tokens = useStore($tokenUsage)
  const syncStatus = useStore($syncStatus)
  const securityStatus = useStore($securityStatus)
  const metrics = useStore($dashboardMetrics)

  useEngineBridge()

  useEffect(() => {
    simulateDashboardData()
    addActivityEvent({ id: 'init-1', type: 'system', message: 'Dashboard initialized', timestamp: Date.now(), status: 'info' })
    addActivityEvent({ id: 'init-2', type: 'health', message: 'System health check completed', timestamp: Date.now() - 10000, status: 'success' })
  }, [])

  const syncColor: Record<string, string> = { idle: 'text-(--ui-text-tertiary)', syncing: 'text-blue-500', error: 'text-red-500' }
  const securityColor: Record<string, string> = { secure: 'text-emerald-500', warning: 'text-amber-500', critical: 'text-red-500' }

  return (
    <ScrollArea className="h-full">
      <div className="mx-auto max-w-6xl space-y-6 p-6">
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold tracking-tight">Production Dashboard</h1>
            <p className="mt-1 text-sm text-(--ui-text-tertiary)">
              System overview, health checks, backups, and runtime management
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 text-xs text-(--ui-text-tertiary)">
              <span className={cn('codicon text-sm', syncColor[syncStatus], syncStatus === 'syncing' ? 'codicon-modifier-spin' : '')} />
              {syncStatus === 'syncing' ? 'Syncing…' : syncStatus === 'error' ? 'Sync Error' : 'Synced'}
            </div>
            <div className="flex items-center gap-1.5 text-xs">
              <span className={cn('codicon text-sm', securityColor[securityStatus])} />
              <span className="capitalize text-(--ui-text-tertiary)">{securityStatus}</span>
            </div>
            <Button onClick={() => navigate('/new')} size="sm">
              New Chat
            </Button>
          </div>
        </header>

        <div className="flex items-center gap-1 rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-bg-tertiary)/20 p-0.5">
          {TABS.map(tab => (
            <button
              className={cn(
                'rounded-md px-3 py-1.5 text-xs font-medium transition-all',
                view === tab.id
                  ? 'bg-(--ui-bg-primary) text-(--ui-text-primary) shadow-sm'
                  : 'text-(--ui-text-tertiary) hover:text-(--ui-text-primary)'
              )}
              key={tab.id}
              onClick={() => setDashboardView(tab.id)}
              type="button"
            >
              {tab.label}
            </button>
          ))}
        </div>

        {view === 'overview' && <OverviewTab health={health} metrics={metrics} stats={stats} tokens={tokens} />}
        {view === 'health' && <HealthTab />}
        {view === 'backup' && <BackupTab />}
        {view === 'runtime' && <RuntimeTab />}
      </div>
    </ScrollArea>
  )
}

function OverviewTab({ stats, health, tokens, metrics }: { stats: any; health: any; tokens: any; metrics: any }) {
  return (
    <div className="space-y-6">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatsCard
          detail={stats?.platform ?? ''}
          icon="dashboard"
          label="CPU"
          trend={metrics ? { direction: stats && stats.cpu > 50 ? 'up' : 'down', value: `${metrics.cpu.average}% avg` } : undefined}
          value={stats ? `${stats.cpu}%` : '—'}
        />
        <StatsCard
          detail={stats ? `${stats.memory.percent}% used` : ''}
          icon="symbol-method"
          label="Memory"
          value={stats ? `${Math.round(stats.memory.used / 1024)}GB / ${Math.round(stats.memory.total / 1024)}GB` : '—'}
        />
        <StatsCard
          detail={`${health?.services?.length ?? 0} services`}
          icon="check"
          label="Status"
          value={health?.overall === 'healthy' ? 'All Systems Go' : health?.overall ?? '—'}
          valueClass={health?.overall === 'healthy' ? 'text-emerald-500' : health?.overall === 'degraded' ? 'text-amber-500' : undefined}
        />
        <StatsCard
          detail={`${tokens.input} in / ${tokens.output} out`}
          icon="symbol-method"
          label="Tokens"
          value={tokens.total > 0 ? tokens.total.toLocaleString() : '0'}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <SystemMetrics />
        <HealthStatus />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <BackupPanel />
        <RuntimePanel />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <AutoRepairPanel />
        <ActivityFeed />
      </div>
    </div>
  )
}

function HealthTab() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold">System Health Details</h2>
          <p className="text-xs text-(--ui-text-tertiary)">Detailed health check results and diagnostics</p>
        </div>
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <HealthStatus />
        <AutoRepairPanel />
      </div>
    </div>
  )
}

function BackupTab() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold">Backup Management</h2>
          <p className="text-xs text-(--ui-text-tertiary)">Configure and manage system backups</p>
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline">Restore Wizard</Button>
          <Button size="sm">Create Backup</Button>
        </div>
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <BackupPanel />
      </div>
    </div>
  )
}

function RuntimeTab() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold">Runtime Manager</h2>
          <p className="text-xs text-(--ui-text-tertiary)">Manage Node.js, Python, Git runtimes and dependencies</p>
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline">Verify All</Button>
          <Button size="sm">Install Missing</Button>
        </div>
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <RuntimePanel />
      </div>
    </div>
  )
}
