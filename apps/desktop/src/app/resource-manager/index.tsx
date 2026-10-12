import { useStore } from '@nanostores/react'
import { useEffect } from 'react'

import { PageDescription, PageHeader, PageShell, PageTitle } from '@/app/page-shell'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { Switch } from '@/components/ui/switch'
import { useI18n } from '@/i18n'
import {
  Activity,
  AlertTriangle,
  Cpu,
  Monitor as HardDrive,
  Monitor,
  Globe as Network,
  Trash2
} from '@/lib/icons'
import { cn } from '@/lib/utils'
import { notify } from '@/store/notifications'
import {
  $resourceManager,
  addAlert,
  clearAlerts,
  setMonitoringActive,
  setResourceTab,
  updateMetric
} from '@/store/resource-manager'
import { $systemStats } from '@/store/system'

export function ResourceManagerView() {
  const { t } = useI18n()
  const state = useStore($resourceManager)
  const stats = useStore($systemStats)

  // Metrics mirror the real backend feed ($systemStats, polled by
  // startBackgroundServices). No synthetic values: the desktop bridge exposes
  // CPU/memory/GPU only — processes, disks and network have no endpoint and
  // render honest empty states instead of fabricated rows.
  useEffect(() => {
    if (!state.monitoringActive || !stats) {
      return
    }

    updateMetric('cpu', Math.round(stats.cpu))
    updateMetric('memory', Math.round(stats.memory.percent))

    if (stats.gpu) {
      updateMetric('gpu', Math.round(stats.gpu.percent))
    }

    if (stats.cpu > 90) {
      addAlert({ id: `alert-${Date.now()}-cpu`, metric: 'cpu', message: 'CPU usage critically high', timestamp: Date.now(), severity: 'critical' })
    }

    if (stats.memory.percent > 90) {
      addAlert({ id: `alert-${Date.now()}-mem`, metric: 'memory', message: 'Memory usage critically high', timestamp: Date.now(), severity: 'critical' })
    }
  }, [state.monitoringActive, stats])

  const clearAllAlerts = () => {
    clearAlerts()
    notify({ kind: 'success', title: 'Resources', message: 'Alerts cleared' })
  }

  const tabs = [
    { id: 'overview' as const, icon: Monitor, label: 'Overview' },
    { id: 'processes' as const, icon: Cpu, label: 'Processes' },
    { id: 'disks' as const, icon: HardDrive, label: 'Disks' },
    { id: 'network' as const, icon: Network, label: 'Network' }
  ]

  return (
    <PageShell
      header={
        <PageHeader className="w-full">
          <div>
            <PageTitle>Resource Manager</PageTitle>
            <PageDescription>Live system metrics from the desktop backend</PageDescription>
          </div>
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Switch checked={state.monitoringActive} onCheckedChange={setMonitoringActive} />
              Live
            </label>
            <Button
              aria-label="Clear alerts"
              className="text-muted-foreground"
              onClick={clearAllAlerts}
              size="icon-xs"
              title="Clear alerts"
              variant="ghost"
            >
              <Trash2 className="size-3.5" />
            </Button>
          </div>
        </PageHeader>
      }
    >
      <div className="flex h-full flex-col gap-0">
        <div className="flex shrink-0 items-center gap-1 border-b border-(--ui-stroke-tertiary)">
          {tabs.map(tab => {
            const Icon = tab.icon

            return (
              <button
                className={cn(
                  'flex items-center gap-1.5 border-b-2 px-4 py-2 text-xs font-medium transition-colors',
                  state.selectedTab === tab.id ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'
                )}
                key={tab.id}
                onClick={() => setResourceTab(tab.id)}
                type="button"
              >
                <Icon className="size-3.5" />
                {tab.label}
              </button>
            )
          })}
        </div>

        {state.selectedTab === 'overview' && (
          <div className="flex-1 space-y-4 overflow-y-auto p-4">
            {!state.monitoringActive ? (
              <p className="rounded-xl border border-dashed border-(--ui-stroke-tertiary) px-4 py-3 text-center text-xs text-muted-foreground" role="status">
                Monitoring is paused — enable Live to mirror the desktop backend metrics.
              </p>
            ) : !stats ? (
              <p className="rounded-xl border border-dashed border-(--ui-stroke-tertiary) px-4 py-3 text-center text-xs text-muted-foreground" role="status">
                Waiting for the desktop backend to report system metrics…
              </p>
            ) : null}
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {state.metrics.map(metric => (
                <MetricCard key={metric.id} metric={metric} />
              ))}
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-xl border border-(--ui-stroke-tertiary) p-4">
                <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">CPU History (60s)</h4>
                <div className="flex items-end gap-px" style={{ height: 64 }}>
                  {state.metrics.find(m => m.id === 'cpu')?.history.map((v, i) => (
                    <div
                      className={cn(
                        'flex-1 rounded-t-sm transition-all',
                        v > 80 ? 'bg-red-500' : v > 60 ? 'bg-amber-500' : 'bg-emerald-500'
                      )}
                      key={i}
                      style={{ height: `${(v / 100) * 100}%` }}
                      title={`${v}%`}
                    />
                  ))}
                </div>
              </div>

              <div className="rounded-xl border border-(--ui-stroke-tertiary) p-4">
                <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Active Alerts</h4>
                {state.alertHistory.length === 0 ? (
                  <p className="py-4 text-center text-xs text-muted-foreground">No active alerts</p>
                ) : (
                  <div className="space-y-1">
                    {state.alertHistory.slice(-5).reverse().map(alert => (
                      <div className="flex items-center gap-2 text-xs" key={alert.id}>
                        <AlertTriangle className={cn(
                          'size-3 shrink-0',
                          alert.severity === 'critical' ? 'text-red-500' : alert.severity === 'warning' ? 'text-amber-500' : 'text-sky-500'
                        )} />
                        <span className="text-foreground/80">{alert.message}</span>
                        <span className="ml-auto text-muted-foreground/60">{new Date(alert.timestamp).toLocaleTimeString()}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {state.selectedTab === 'processes' && (
          <div className="flex-1 overflow-y-auto p-4">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-(--ui-stroke-tertiary) text-muted-foreground">
                  <th className="pb-2 font-medium">Name</th>
                  <th className="pb-2 font-medium">PID</th>
                  <th className="pb-2 font-medium">CPU %</th>
                  <th className="pb-2 font-medium">Memory</th>
                  <th className="pb-2 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {state.processes.length === 0 ? (
                  <tr>
                    <td className="py-6 text-center text-xs text-muted-foreground" colSpan={5}>
                      No process data — the desktop backend does not report per-process stats.
                    </td>
                  </tr>
                ) : (
                state.processes.map(p => (
                  <tr className="border-b border-(--ui-stroke-tertiary)/50" key={p.id}>
                    <td className="py-1.5 font-medium text-foreground">{p.name}</td>
                    <td className="py-1.5 text-muted-foreground">{p.pid}</td>
                    <td className="py-1.5">
                      <span className={cn(p.cpu > 50 ? 'text-red-500' : p.cpu > 20 ? 'text-amber-500' : 'text-foreground')}>
                        {p.cpu}%
                      </span>
                    </td>
                    <td className="py-1.5 text-muted-foreground">{p.memory} MB</td>
                    <td className="py-1.5">
                      <Badge className={cn(
                        p.status === 'running' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-muted text-muted-foreground'
                      )} variant="secondary">{p.status}</Badge>
                    </td>
                  </tr>
                )))}
              </tbody>
            </table>
          </div>
        )}

        {state.selectedTab === 'disks' && (
          <div className="flex-1 space-y-3 overflow-y-auto p-4">
            {state.disks.length === 0 ? (
              <p className="py-8 text-center text-xs text-muted-foreground">
                No disk data — the desktop backend does not report disk usage.
              </p>
            ) : (
            state.disks.map(disk => (
              <div className="rounded-xl border border-(--ui-stroke-tertiary) p-4" key={disk.mount}>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-foreground">{disk.mount}</span>
                  <span className="text-xs text-muted-foreground">{disk.used} GB / {disk.total} GB</span>
                </div>
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-(--ui-bg-quinary)">
                  <div
                    className={cn(
                      'h-full rounded-full transition-all',
                      disk.percent > 85 ? 'bg-red-500' : disk.percent > 70 ? 'bg-amber-500' : 'bg-emerald-500'
                    )}
                    style={{ width: `${disk.percent}%` }}
                  />
                </div>
                <div className="mt-1 text-right text-[0.55rem] text-muted-foreground">{disk.percent}% used</div>
              </div>
            )))}
          </div>
        )}

        {state.selectedTab === 'network' && (
          <div className="flex-1 space-y-4 overflow-y-auto p-4">
            {!state.network ? (
              <p className="py-8 text-center text-xs text-muted-foreground">
                No network data — the desktop backend does not report traffic stats.
              </p>
            ) : (
            <div className="grid gap-4 sm:grid-cols-3">
              <NetworkStatCard icon={Network} label="Download" value={`${state.network.rx} MB/s`} />
              <NetworkStatCard icon={Network} label="Upload" value={`${state.network.tx} MB/s`} />
              <NetworkStatCard icon={Activity} label="Connections" value={String(state.network.connections)} />
            </div>
            )}
          </div>
        )}
      </div>
    </PageShell>
  )
}

function MetricCard({ metric }: { metric: { id: string; label: string; value: number; unit: string; max: number; thresholds: { warning: number; critical: number } } }) {
  const ratio = metric.value / metric.max

  return (
    <div className="rounded-xl border border-(--ui-stroke-tertiary) p-4">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-muted-foreground">{metric.label}</span>
        <Codicon name={metric.id === 'cpu' ? 'cpu' : metric.id === 'memory' ? 'database' : metric.id === 'gpu' ? 'symbol-method' : 'file-directory'} size="0.875rem" />
      </div>
      <div className="mt-2 flex items-baseline gap-1">
        <span className="text-2xl font-semibold tabular-nums">{metric.value}</span>
        <span className="text-xs text-muted-foreground">{metric.unit}</span>
      </div>
      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-(--ui-bg-quinary)">
        <div
          className={cn(
            'h-full rounded-full transition-all',
            ratio > 0.8 ? 'bg-red-500' : ratio > 0.6 ? 'bg-amber-500' : 'bg-emerald-500'
          )}
          style={{ width: `${Math.min(ratio * 100, 100)}%` }}
        />
      </div>
    </div>
  )
}

function NetworkStatCard({ icon: Icon, label, value }: { icon: any; label: string; value: string }) {
  return (
    <div className="rounded-xl border border-(--ui-stroke-tertiary) p-4">
      <div className="flex items-center gap-2">
        <Icon className="size-4 text-muted-foreground" />
        <span className="text-xs font-medium text-muted-foreground">{label}</span>
      </div>
      <div className="mt-2 text-lg font-semibold tabular-nums">{value}</div>
    </div>
  )
}
