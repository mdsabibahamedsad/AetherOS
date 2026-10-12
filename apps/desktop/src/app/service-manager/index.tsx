import { useStore } from '@nanostores/react'
import { useEffect } from 'react'

import { PageDescription, PageHeader, PageShell, PageTitle } from '@/app/page-shell'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import {
  Play,
  RefreshCw,
  Square,
  Trash2
} from '@/lib/icons'
import { cn } from '@/lib/utils'
import { notify } from '@/store/notifications'
import {
  $serviceManager,
  addServiceLog,
  selectService,
  setAutoRefresh,
  setLogFilter,
  setServiceManagerTab,
  toggleServiceAutoRestart
} from '@/store/service-manager'
import type { ManagedService } from '@/store/service-manager'

const STATUS_BADGES: Record<string, string> = {
  running: 'bg-emerald-500/10 text-emerald-500',
  stopped: 'bg-muted text-muted-foreground',
  error: 'bg-red-500/10 text-red-500',
  starting: 'bg-amber-500/10 text-amber-500',
  stopping: 'bg-amber-500/10 text-amber-500'
}

const STATUS_PULSE: Record<string, string> = {
  running: 'bg-emerald-500',
  stopped: 'bg-muted-foreground',
  error: 'bg-red-500',
  starting: 'bg-amber-500 animate-pulse',
  stopping: 'bg-amber-500 animate-pulse'
}

function formatUptime(seconds?: number): string {
  if (!seconds) {return '—'}
  const d = Math.floor(seconds / 86400)
  const h = Math.floor((seconds % 86400) / 3600)

  if (d > 0) {return `${d}d ${h}h`}
  const m = Math.floor((seconds % 3600) / 60)

  if (h > 0) {return `${h}h ${m}m`}

  return `${m}m`
}

export function ServiceManagerView() {
  const state = useStore($serviceManager)

  useEffect(() => {
    if (!state.autoRefresh) {return}

    const interval = setInterval(() => {
      const logs = [
        { id: `log-${Date.now()}`, serviceId: 'gateway', timestamp: Date.now(), level: 'info' as const, message: 'Heartbeat received' },
        { id: `log-${Date.now() + 1}`, serviceId: 'scheduler', timestamp: Date.now(), level: 'debug' as const, message: 'Tick processed, 0 jobs due' },
        { id: `log-${Date.now() + 2}`, serviceId: 'plugin-host', timestamp: Date.now(), level: 'info' as const, message: 'Plugin sandbox active, 4 plugins loaded' }
      ]

      logs.forEach(l => addServiceLog(l))
    }, 5000)

    return () => clearInterval(interval)
  }, [state.autoRefresh])

  const tabs = [
    { id: 'dashboard' as const, label: 'Dashboard' },
    { id: 'services' as const, label: 'Services' },
    { id: 'logs' as const, label: 'Logs' },
    { id: 'settings' as const, label: 'Settings' }
  ]

  const selectedService = state.services.find(s => s.id === state.selectedServiceId)

  const filteredLogs = state.logs.filter(l => {
    if (state.logFilter !== 'all' && l.level !== state.logFilter) {return false}

    if (state.selectedServiceId && l.serviceId !== state.selectedServiceId) {return false}

    return true
  })

  return (
    <PageShell
      header={
        <PageHeader className="w-full">
          <div>
            <PageTitle>Service Manager</PageTitle>
            <PageDescription>Manage background services and monitor system health</PageDescription>
          </div>
          <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Switch checked={state.autoRefresh} onCheckedChange={setAutoRefresh} />
            Auto-refresh
          </label>
        </PageHeader>
      }
    >
      <div className="flex h-full flex-col gap-0">
        <div className="flex shrink-0 items-center gap-1 border-b border-(--ui-stroke-tertiary)">
          {tabs.map(tab => (
            <button
              className={cn(
                'flex items-center gap-1.5 border-b-2 px-4 py-2 text-xs font-medium transition-colors',
                state.selectedTab === tab.id ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'
              )}
              key={tab.id}
              onClick={() => setServiceManagerTab(tab.id)}
              type="button"
            >
              {tab.label}
            </button>
          ))}
        </div>

        {state.selectedTab === 'dashboard' && (
          <div className="flex-1 space-y-4 overflow-y-auto p-4">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <SummaryCard label="Total Services" value={state.services.length.toString()} />
              <SummaryCard color="text-emerald-500" label="Running" value={state.services.filter(s => s.status === 'running').length.toString()} />
              <SummaryCard color="text-muted-foreground" label="Stopped" value={state.services.filter(s => s.status === 'stopped').length.toString()} />
              <SummaryCard color="text-red-500" label="Errors" value={state.services.filter(s => s.status === 'error').length.toString()} />
            </div>
            <div className="space-y-2">
              {state.services.slice(0, 4).map(service => (
                <ServiceRow key={service.id} onSelect={() => { selectService(service.id); setServiceManagerTab('services') }} selected={state.selectedServiceId === service.id} service={service} />
              ))}
            </div>
          </div>
        )}

        {state.selectedTab === 'services' && (
          <div className="flex min-h-0 flex-1">
            <div className="w-64 shrink-0 overflow-y-auto border-r border-(--ui-stroke-tertiary) p-2">
              {state.services.map(service => (
                <button
                  className={cn(
                    'flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-xs transition-colors',
                    state.selectedServiceId === service.id ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:bg-accent/60 hover:text-foreground'
                  )}
                  key={service.id}
                  onClick={() => selectService(service.id)}
                  type="button"
                >
                  <span className={cn('size-1.5 rounded-full shrink-0', STATUS_PULSE[service.status])} />
                  <span className="truncate font-medium">{service.name}</span>
                </button>
              ))}
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              {selectedService ? (
                <ServiceDetail service={selectedService} />
              ) : (
                <p className="py-8 text-center text-xs text-muted-foreground">Select a service to view details</p>
              )}
            </div>
          </div>
        )}

        {state.selectedTab === 'logs' && (
          <div className="flex min-h-0 flex-1 flex-col">
            <div className="flex shrink-0 items-center gap-2 border-b border-(--ui-stroke-tertiary) px-3 py-1.5">
              {(['all', 'debug', 'info', 'warn', 'error'] as const).map(level => (
                <button
                  className={cn(
                    'rounded-md px-2 py-0.5 text-[0.6rem] font-medium transition-colors',
                    state.logFilter === level ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:text-foreground'
                  )}
                  key={level}
                  onClick={() => setLogFilter(level)}
                  type="button"
                >
                  {level === 'all' ? 'All' : level.charAt(0).toUpperCase() + level.slice(1)}
                </button>
              ))}
              <Button
                className="ml-auto text-muted-foreground"
                onClick={() => notify({ kind: 'success', title: 'Logs', message: 'Log buffer cleared' })}
                size="icon-xs"
                variant="ghost"
              >
                <Trash2 className="size-3" />
              </Button>
            </div>
            <div className="flex-1 overflow-y-auto p-3 font-mono text-[0.6rem] leading-relaxed">
              {filteredLogs.length === 0 ? (
                <span className="text-muted-foreground/60">No log entries</span>
              ) : filteredLogs.slice(-100).reverse().map(log => (
                <div className="flex gap-2 py-0.5" key={log.id}>
                  <span className={cn(
                    'shrink-0 text-[0.5rem] font-semibold uppercase',
                    log.level === 'error' ? 'text-red-500' : log.level === 'warn' ? 'text-amber-500' : log.level === 'info' ? 'text-sky-500' : 'text-muted-foreground'
                  )}>
                    {log.level}
                  </span>
                  <span className="shrink-0 text-muted-foreground/60">{new Date(log.timestamp).toLocaleTimeString()}</span>
                  <span className="text-muted-foreground/40">[{log.serviceId}]</span>
                  <span className="text-foreground/80">{log.message}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {state.selectedTab === 'settings' && (
          <div className="flex-1 space-y-4 overflow-y-auto p-4">
            <div className="rounded-xl border border-(--ui-stroke-tertiary) p-4">
              <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Service Auto-Restart</h4>
              <div className="space-y-2">
                {state.services.filter(s => s.status === 'running' || s.status === 'stopped').map(s => (
                  <label className="flex items-center justify-between gap-2 text-xs" key={s.id}>
                    <span className="text-foreground">{s.name}</span>
                    <Switch checked={s.autoRestart} onCheckedChange={() => toggleServiceAutoRestart(s.id)} />
                  </label>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </PageShell>
  )
}

function SummaryCard({ label, value, color = 'text-foreground' }: { label: string; value: string; color?: string }) {
  return (
    <div className="rounded-xl border border-(--ui-stroke-tertiary) p-3">
      <div className="text-[0.6rem] font-medium uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className={cn('mt-0.5 text-lg font-semibold tabular-nums', color)}>{value}</div>
    </div>
  )
}

function ServiceRow({ service, selected, onSelect }: { service: ManagedService; selected: boolean; onSelect: () => void }) {
  return (
    <button
      className={cn(
        'flex w-full items-center gap-3 rounded-lg border px-3 py-2 text-left text-xs transition-colors',
        selected ? 'border-primary/30 bg-accent/60' : 'border-(--ui-stroke-tertiary) hover:border-(--ui-stroke-secondary)'
      )}
      onClick={onSelect}
      type="button"
    >
      <span className={cn('size-2 rounded-full shrink-0', STATUS_PULSE[service.status])} />
      <div className="min-w-0 flex-1">
        <div className="font-medium text-foreground">{service.name}</div>
        <div className="text-muted-foreground">{service.description}</div>
      </div>
      <Badge className={STATUS_BADGES[service.status]} variant="secondary">{service.status}</Badge>
      {service.uptime && <span className="text-muted-foreground/60">{formatUptime(service.uptime)}</span>}
    </button>
  )
}

function ServiceDetail({ service }: { service: ManagedService }) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <span className={cn('size-3 rounded-full', STATUS_PULSE[service.status])} />
        <div>
          <h3 className="text-sm font-semibold text-foreground">{service.name}</h3>
          <p className="text-xs text-muted-foreground">{service.description}</p>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <DetailField label="Status" value={service.status} />
        <DetailField label="Uptime" value={formatUptime(service.uptime)} />
        <DetailField label="Memory" value={service.memory ? `${service.memory} MB` : '—'} />
        <DetailField label="CPU" value={service.cpu ? `${service.cpu}%` : '—'} />
        <DetailField label="PID" value={service.pid ? String(service.pid) : '—'} />
        <DetailField label="Version" value={service.version ?? '—'} />
        <DetailField label="Auto Restart" value={service.autoRestart ? 'Enabled' : 'Disabled'} />
        {service.lastError && <DetailField label="Last Error" value={service.lastError} />}
      </div>
      <div className="flex gap-2">
        <Button disabled={service.status === 'running'} size="xs" variant="text">
          <Play className="size-3 mr-1" /> Start
        </Button>
        <Button disabled={service.status === 'stopped'} size="xs" variant="text">
          <Square className="size-3 mr-1" /> Stop
        </Button>
        <Button size="xs" variant="text">
          <RefreshCw className="size-3 mr-1" /> Restart
        </Button>
      </div>
    </div>
  )
}

function DetailField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[0.55rem] font-medium uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className="mt-0.5 text-xs text-foreground">{value}</div>
    </div>
  )
}
