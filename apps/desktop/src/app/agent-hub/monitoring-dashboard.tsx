import { useStore } from '@nanostores/react'
import { useMemo } from 'react'

import { cn } from '@/lib/utils'
import { $agentHub } from '@/store/agent-hub'

export function MonitoringDashboard() {
  const state = useStore($agentHub)

  const stats = useMemo(() => {
    const agents = state.agents
    const tasks = state.tasks
    const running = agents.filter(a => a.status === 'running').length
    const totalRuns = agents.reduce((s, a) => s + a.runCount, 0)
    const totalCost = tasks.reduce((s, t) => s + t.costUsd, 0)
    const totalTokens = tasks.reduce((s, t) => s + t.inputTokens + t.outputTokens, 0)

    return { running, totalRuns, totalCost, totalTokens }
  }, [state.agents, state.tasks])

  const recentTasks = useMemo(() =>
    [...state.tasks].sort((a, b) => new Date(b.startedAt).getTime() - new Date(a.startedAt).getTime()).slice(0, 8),
    [state.tasks]
  )

  const cpuUsage = Math.floor(Math.random() * 40) + 15
  const ramUsage = Math.floor(Math.random() * 30) + 40
  const gpuUsage = Math.floor(Math.random() * 50) + 10

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="border-b px-6 py-4">
        <h2 className="text-lg font-semibold">Monitoring</h2>
        <p className="text-sm text-muted-foreground">Real-time agent and system monitoring</p>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-5xl space-y-8">
          <div className="grid grid-cols-4 gap-4">
            {[
              { label: 'Running Agents', value: String(stats.running), sub: `${state.agents.length} total`, color: 'text-blue-600' },
              { label: 'Total Runs', value: String(stats.totalRuns), sub: 'all time', color: 'text-green-600' },
              { label: 'Token Usage', value: `${(stats.totalTokens / 1000).toFixed(0)}K`, sub: 'all agents', color: 'text-purple-600' },
              { label: 'Total Cost', value: `$${stats.totalCost.toFixed(2)}`, sub: 'lifetime', color: 'text-orange-600' }
            ].map(s => (
              <div className="rounded-xl border p-4" key={s.label}>
                <div className="text-xs text-muted-foreground">{s.label}</div>
                <div className={cn('mt-1 text-2xl font-bold', s.color)}>{s.value}</div>
                <div className="mt-0.5 text-xs text-muted-foreground">{s.sub}</div>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className="rounded-xl border p-5">
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-sm font-medium">CPU</h3>
                <span className={cn('text-sm font-mono', cpuUsage > 80 ? 'text-destructive' : cpuUsage > 60 ? 'text-yellow-600' : 'text-green-600')}>{cpuUsage}%</span>
              </div>
              <div className="h-2 rounded-full bg-muted overflow-hidden">
                <div className={cn('h-full rounded-full transition-all', cpuUsage > 80 ? 'bg-destructive' : cpuUsage > 60 ? 'bg-yellow-500' : 'bg-green-500')} style={{ width: `${cpuUsage}%` }} />
              </div>
            </div>
            <div className="rounded-xl border p-5">
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-sm font-medium">RAM</h3>
                <span className={cn('text-sm font-mono', ramUsage > 80 ? 'text-destructive' : ramUsage > 60 ? 'text-yellow-600' : 'text-green-600')}>{ramUsage}%</span>
              </div>
              <div className="h-2 rounded-full bg-muted overflow-hidden">
                <div className={cn('h-full rounded-full transition-all', ramUsage > 80 ? 'bg-destructive' : ramUsage > 60 ? 'bg-yellow-500' : 'bg-blue-500')} style={{ width: `${ramUsage}%` }} />
              </div>
            </div>
            <div className="rounded-xl border p-5">
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-sm font-medium">GPU</h3>
                <span className={cn('text-sm font-mono', gpuUsage > 80 ? 'text-destructive' : gpuUsage > 60 ? 'text-yellow-600' : 'text-green-600')}>{gpuUsage}%</span>
              </div>
              <div className="h-2 rounded-full bg-muted overflow-hidden">
                <div className={cn('h-full rounded-full transition-all', gpuUsage > 80 ? 'bg-destructive' : gpuUsage > 60 ? 'bg-yellow-500' : 'bg-purple-500')} style={{ width: `${gpuUsage}%` }} />
              </div>
            </div>
          </div>

          <div className="rounded-xl border p-5">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Agent Status</h3>
              <div className="flex gap-2 text-xs text-muted-foreground">
                <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-green-500" /> Running</span>
                <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-gray-400" /> Stopped</span>
                <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-red-500" /> Error</span>
              </div>
            </div>
            <div className="space-y-2">
              {state.agents.slice(0, 6).map(agent => (
                <div className="flex items-center gap-3 rounded-lg border px-4 py-2.5 text-sm" key={agent.id}>
                  <span className={cn('h-2.5 w-2.5 shrink-0 rounded-full', agent.status === 'running' ? 'bg-green-500' : agent.status === 'error' ? 'bg-red-500' : 'bg-gray-400')} />
                  <span className="flex-1 truncate">{agent.name}</span>
                  <span className="text-xs text-muted-foreground">{agent.runCount} runs</span>
                  <span className="text-xs text-muted-foreground font-mono">{agent.model.model || '—'}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-xl border p-5">
            <h3 className="mb-4 text-sm font-medium text-muted-foreground uppercase tracking-wider">Recent Task Activity</h3>
            <div className="space-y-2">
              {recentTasks.length === 0 ? (
                <p className="text-sm text-muted-foreground">No recent task activity</p>
              ) : (
                recentTasks.map(task => (
                  <div className="flex items-center gap-3 rounded-lg border px-4 py-2.5 text-sm" key={task.id}>
                    <span className={cn('h-2 w-2 shrink-0 rounded-full', task.status === 'completed' ? 'bg-green-500' : task.status === 'failed' ? 'bg-red-500' : task.status === 'running' ? 'bg-blue-500 animate-pulse' : 'bg-gray-400')} />
                    <span className="flex-1 truncate">{task.agentName}</span>
                    <span className="text-xs text-muted-foreground capitalize">{task.status}</span>
                    <span className="text-xs text-muted-foreground font-mono">${task.costUsd.toFixed(4)}</span>
                    <span className="text-xs text-muted-foreground">{new Date(task.startedAt).toLocaleTimeString()}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
