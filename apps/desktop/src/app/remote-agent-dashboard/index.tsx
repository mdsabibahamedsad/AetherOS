import { useCallback, useState } from 'react'

import { PageDescription, PageHeader, PageShell, PageTitle } from '@/app/page-shell'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { cn } from '@/lib/utils'
import { notify, notifyError } from '@/store/notifications'
import {
  $remoteAgentStatus,
  $remoteConnected,
  $remoteInstances,
  $remoteLoading,
  $remoteLogLevelFilter,
  $remoteLogs,
  $remoteTasks,
  type AgentStatus,
  getActiveInstance,
  getFilteredLogs,
  pauseAgent,
  refreshLogs,
  refreshTasks,
  type RemoteLogEntry,
  type RemoteTask,
  restartAgent,
  resumeAgent,
  setLogLevelFilter,
  startAgent,
  stopAgent,
} from '@/store/remote-agent'

const AGENT_ACTIONS: { status: AgentStatus; label: string; icon: string }[] = [
  { status: 'running', label: 'Start', icon: 'play' },
  { status: 'stopped', label: 'Stop', icon: 'stop' },
  { status: 'paused', label: 'Pause', icon: 'pause' },
  { status: 'paused', label: 'Resume', icon: 'play' },
  { status: 'error', label: 'Restart', icon: 'refresh' },
]

const LOG_LEVELS = ['all', 'debug', 'info', 'warn', 'error'] as const

const SAMPLE_LOGS: RemoteLogEntry[] = Array.from({ length: 30 }, (_, i) => ({
  id: `log-${i}`,
  timestamp: new Date(Date.now() - (30 - i) * 60000).toISOString(),
  level: (['debug', 'info', 'warn', 'error'] as const)[Math.floor(Math.random() * 4)],
  source: ['agent', 'sync', 'gateway', 'http', 'system'][Math.floor(Math.random() * 5)],
  message: [
    'Processing incoming message from gateway',
    'Sync cycle completed — 12 items pushed',
    'Memory snapshot saved successfully',
    'Connection health check passed',
    'Webhook event queued for processing',
    'Session checkpoint created',
    'Tool execution completed',
    'Model inference returned in 1.2s',
    'Background task finished',
    'Configuration reloaded from disk',
  ][Math.floor(Math.random() * 10)],
}))

const SAMPLE_TASKS: RemoteTask[] = [
  { id: 'task-1', name: 'Index Knowledge Base', status: 'running', progress: 65, startedAt: new Date(Date.now() - 120000).toISOString(), completedAt: null, errorMessage: null },
  { id: 'task-2', name: 'Sync Files to Cloud', status: 'running', progress: 30, startedAt: new Date(Date.now() - 60000).toISOString(), completedAt: null, errorMessage: null },
  { id: 'task-3', name: 'Process Email Queue', status: 'queued', progress: 0, startedAt: null, completedAt: null, errorMessage: null },
  { id: 'task-4', name: 'Backup Memory Store', status: 'completed', progress: 100, startedAt: new Date(Date.now() - 3600000).toISOString(), completedAt: new Date(Date.now() - 3540000).toISOString(), errorMessage: null },
  { id: 'task-5', name: 'Update Plugin Index', status: 'failed', progress: 45, startedAt: new Date(Date.now() - 7200000).toISOString(), completedAt: new Date(Date.now() - 7140000).toISOString(), errorMessage: 'Connection timeout to plugin registry' },
]

export function RemoteAgentDashboardView() {
  const agentStatus = $remoteAgentStatus.get()
  const connected = $remoteConnected.get()
  const loading = $remoteLoading.get()
  const logLevelFilter = $remoteLogLevelFilter.get()

  const logs = $remoteLogs.get().length > 0 ? getFilteredLogs() : SAMPLE_LOGS.filter(l => logLevelFilter === 'all' || l.level === logLevelFilter)
  const tasks = $remoteTasks.get().length > 0 ? $remoteTasks.get() : SAMPLE_TASKS
  const activeInstance = getActiveInstance()
  const instances = $remoteInstances.get()

  const [autoRefresh, setAutoRefresh] = useState(false)

  const handleStart = useCallback(() => {
    try {
      startAgent()
      notify({ kind: 'success', title: 'Agent Started', message: 'Remote agent is now running' })
    } catch (err) { notifyError(err, 'Failed to start agent') }
  }, [])

  const handleStop = useCallback(() => {
    try {
      stopAgent()
      notify({ kind: 'info', title: 'Agent Stopped', message: 'Remote agent has been stopped' })
    } catch (err) { notifyError(err, 'Failed to stop agent') }
  }, [])

  const handlePause = useCallback(() => {
    try {
      pauseAgent()
      notify({ kind: 'info', title: 'Agent Paused', message: 'Remote agent is paused' })
    } catch (err) { notifyError(err, 'Failed to pause agent') }
  }, [])

  const handleResume = useCallback(() => {
    try {
      resumeAgent()
      notify({ kind: 'info', title: 'Agent Resumed', message: 'Remote agent is running again' })
    } catch (err) { notifyError(err, 'Failed to resume agent') }
  }, [])

  const handleRestart = useCallback(() => {
    try {
      restartAgent()
      notify({ kind: 'info', title: 'Agent Restarting', message: 'Remote agent is restarting...' })
    } catch (err) { notifyError(err, 'Failed to restart agent') }
  }, [])

  const handleRefreshLogs = useCallback(() => {
    refreshLogs()
    notify({ kind: 'info', title: 'Logs Refreshed', message: 'Log entries updated' })
  }, [])

  const handleRefreshTasks = useCallback(() => {
    refreshTasks()
    notify({ kind: 'info', title: 'Tasks Refreshed', message: 'Task list updated' })
  }, [])

  const statusVariant = (st: AgentStatus) => {
    switch (st) {
      case 'running': return 'default' as const

      case 'stopped': return 'outline' as const

      case 'paused': return 'muted' as const

      case 'starting':

 case 'stopping': return 'muted' as const

      case 'error': return 'destructive' as const
    }
  }

  const taskStatusVariant = (st: RemoteTask['status']) => {
    switch (st) {
      case 'running': return 'default' as const

      case 'completed': return 'muted' as const

      case 'failed': return 'destructive' as const

      case 'queued': return 'outline' as const
    }
  }

  const logLevelColor = (level: string) => {
    switch (level) {
      case 'error': return 'text-destructive'

      case 'warn': return 'text-amber-500'

      case 'info': return 'text-primary'

      case 'debug': return 'text-muted-foreground'

      default: return ''
    }
  }

  if (!connected) {
    return (
      <PageShell
        header={
          <PageHeader>
            <PageTitle>Remote Agent Dashboard</PageTitle>
            <PageDescription>Monitor and control remote AetherOS agents</PageDescription>
          </PageHeader>
        }
      >
        <div className="grid min-h-52 place-items-center text-center">
          <div>
            <Codicon className="text-muted-foreground/40" name="server" size="2rem" />
            <p className="mt-2 text-sm font-medium text-muted-foreground">Not Connected</p>
            <p className="mt-1 text-xs text-muted-foreground/60">
              {instances.length > 0
                ? 'Connect to a remote instance from the Remote Instances page'
                : 'Add and connect to a remote instance first'}
            </p>
          </div>
        </div>
      </PageShell>
    )
  }

  return (
    <PageShell
      header={
        <PageHeader className="w-full">
          <div className="flex items-center justify-between">
            <div>
              <PageTitle>Remote Agent Dashboard</PageTitle>
              <PageDescription>
                {activeInstance
                  ? `${activeInstance.name} — ${activeInstance.host}:${activeInstance.port}`
                  : 'Monitor and control remote AetherOS agents'}
              </PageDescription>
            </div>
            <div className="flex items-center gap-2">
              <Badge className="text-[0.6rem]" variant={connected ? 'default' : 'outline'}>
                <Codicon name={connected ? 'plug' : 'debug-disconnect'} size="0.6rem" />
                {connected ? 'Connected' : 'Disconnected'}
              </Badge>
            </div>
          </div>
        </PageHeader>
      }
    >
      <div className="grid grid-cols-4 gap-4">
        <div className="rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-chat-surface-background) p-3">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Codicon name="symbol-method" size="0.85rem" />
            <span>CPU</span>
          </div>
          <p className="mt-1 text-lg font-semibold">{agentStatus.cpu}%</p>
        </div>
        <div className="rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-chat-surface-background) p-3">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Codicon name="database" size="0.85rem" />
            <span>Memory</span>
          </div>
          <p className="mt-1 text-lg font-semibold">{agentStatus.memory}%</p>
        </div>
        <div className="rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-chat-surface-background) p-3">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Codicon name="history" size="0.85rem" />
            <span>Uptime</span>
          </div>
          <p className="mt-1 text-lg font-semibold">{formatUptime(agentStatus.uptime)}</p>
        </div>
        <div className="rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-chat-surface-background) p-3">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Codicon name="checklist" size="0.85rem" />
            <span>Tasks</span>
          </div>
          <p className="mt-1 text-lg font-semibold">{tasks.filter(t => t.status === 'running').length} active</p>
        </div>
      </div>

      <div className="mt-4 flex items-center gap-2">
        <Badge className="text-[0.6rem]" variant={statusVariant(agentStatus.status)}>
          <Codicon
            name={agentStatus.status === 'running' ? 'play' : agentStatus.status === 'paused' ? 'pause' : agentStatus.status === 'error' ? 'error' : 'stop'}
            size="0.6rem"
          />
          <span className="capitalize">{agentStatus.status}</span>
        </Badge>
        <div className="ml-auto flex items-center gap-1.5">
          {agentStatus.status === 'stopped' && (
            <Button disabled={loading} onClick={handleStart} size="sm"><Codicon name="play" size="0.75rem" />Start</Button>
          )}
          {agentStatus.status === 'running' && (
            <>
              <Button disabled={loading} onClick={handlePause} size="sm" variant="outline"><Codicon name="pause" size="0.75rem" />Pause</Button>
              <Button disabled={loading} onClick={handleStop} size="sm" variant="outline"><Codicon name="stop" size="0.75rem" />Stop</Button>
            </>
          )}
          {agentStatus.status === 'paused' && (
            <>
              <Button disabled={loading} onClick={handleResume} size="sm"><Codicon name="play" size="0.75rem" />Resume</Button>
              <Button disabled={loading} onClick={handleStop} size="sm" variant="outline"><Codicon name="stop" size="0.75rem" />Stop</Button>
            </>
          )}
          {agentStatus.status === 'error' && (
            <Button disabled={loading} onClick={handleRestart} size="sm"><Codicon name="refresh" size="0.75rem" />Restart</Button>
          )}
        </div>
      </div>

      {agentStatus.errorMessage && (
        <div className="mt-2 flex items-center gap-2 rounded-md bg-destructive/10 px-3 py-2">
          <Codicon className="text-destructive" name="error" size="0.85rem" />
          <span className="text-xs text-destructive">{agentStatus.errorMessage}</span>
        </div>
      )}

      <div className="mt-4 grid grid-cols-2 gap-4">
        <div>
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Task List</h3>
            <Button className="text-xs" onClick={handleRefreshTasks} size="sm" variant="ghost">
              <Codicon name="refresh" size="0.65rem" />
            </Button>
          </div>
          <div className="space-y-1">
            {tasks.map(task => (
              <div
                className="rounded-md border border-(--ui-stroke-tertiary) px-2.5 py-2 text-xs"
                key={task.id}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Codicon
                      className={cn(
                        task.status === 'running' && 'animate-spin text-primary',
                        task.status === 'completed' && 'text-emerald-500',
                        task.status === 'failed' && 'text-destructive',
                        task.status === 'queued' && 'text-muted-foreground',
                      )}
                      name={
                        task.status === 'running' ? 'sync' :
                        task.status === 'completed' ? 'check' :
                        task.status === 'failed' ? 'error' : 'clock'
                      }
                      size="0.7rem"
                    />
                    <span className="font-medium">{task.name}</span>
                  </div>
                  <Badge className="text-[0.5rem]" variant={taskStatusVariant(task.status)}>
                    {task.status}
                  </Badge>
                </div>
                {(task.status === 'running' || task.status === 'queued') && (
                  <div className="mt-1.5 flex items-center gap-2">
                    <div className="h-1 flex-1 overflow-hidden rounded-full bg-(--ui-stroke-tertiary)">
                      <div
                        className="h-full rounded-full bg-primary transition-all"
                        style={{ width: `${task.progress}%` }}
                      />
                    </div>
                    <span className="text-[0.55rem] text-muted-foreground">{task.progress}%</span>
                  </div>
                )}
                {task.errorMessage && (
                  <p className="mt-1 text-[0.55rem] text-destructive">{task.errorMessage}</p>
                )}
              </div>
            ))}
          </div>
        </div>

        <div>
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Logs</h3>
            <div className="flex items-center gap-1.5">
              <Select onValueChange={v => setLogLevelFilter(v)} value={logLevelFilter}>
                <SelectTrigger className="h-7 w-20 text-[0.6rem]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {LOG_LEVELS.map(l => (
                    <SelectItem key={l} value={l}>
                      <span className="capitalize">{l === 'all' ? 'All' : l === 'warn' ? 'Warning' : l === 'info' ? 'Info' : l === 'debug' ? 'Debug' : 'Error'}</span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button className="text-xs" onClick={handleRefreshLogs} size="sm" variant="ghost">
                <Codicon name="refresh" size="0.65rem" />
              </Button>
            </div>
          </div>
          <div className="max-h-80 space-y-0.5 overflow-y-auto rounded-lg border border-(--ui-stroke-tertiary) bg-(--ui-bg-quinary) p-1.5 font-mono">
            {logs.length === 0 && (
              <p className="p-2 text-xs text-muted-foreground">No log entries</p>
            )}
            {logs.slice(0, 50).map(log => (
              <div className="flex items-start gap-2 px-1.5 py-0.5 text-[0.6rem]" key={log.id}>
                <span className="shrink-0 text-muted-foreground">
                  {new Date(log.timestamp).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </span>
                <span className={cn('shrink-0 w-8 font-semibold uppercase', logLevelColor(log.level))}>
                  {log.level}
                </span>
                <span className="truncate text-foreground/80">{log.message}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </PageShell>
  )
}

function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)

  if (h > 0) {return `${h}h ${m}m`}

  if (m > 0) {return `${m}m`}

  return `${Math.floor(seconds)}s`
}
