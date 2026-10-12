import { useStore } from '@nanostores/react'
import { useMemo, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { $agentHub, updateTask } from '@/store/agent-hub'

const STATUS_CONFIG: Record<string, { color: string; label: string; bg: string }> = {
  running: { color: 'text-blue-600', label: 'Running', bg: 'bg-blue-500/10 border-blue-500/30' },
  queued: { color: 'text-yellow-600', label: 'Queued', bg: 'bg-yellow-500/10 border-yellow-500/30' },
  completed: { color: 'text-green-600', label: 'Completed', bg: 'bg-green-500/10 border-green-500/30' },
  failed: { color: 'text-red-600', label: 'Failed', bg: 'bg-red-500/10 border-red-500/30' },
  cancelled: { color: 'text-gray-500', label: 'Cancelled', bg: 'bg-gray-500/10 border-gray-500/30' }
}

export function TaskManager() {
  const state = useStore($agentHub)
  const [filter, setFilter] = useState<string>('all')
  const [expanded, setExpanded] = useState<string | null>(null)

  const filtered = useMemo(() => {
    if (filter === 'all') {return state.tasks}

    return state.tasks.filter(t => t.status === filter)
  }, [state.tasks, filter])

  const stats = useMemo(() => ({
    running: state.tasks.filter(t => t.status === 'running').length,
    queued: state.tasks.filter(t => t.status === 'queued').length,
    completed: state.tasks.filter(t => t.status === 'completed').length,
    failed: state.tasks.filter(t => t.status === 'failed').length
  }), [state.tasks])

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="border-b px-6 py-4">
        <h2 className="text-lg font-semibold">Task Manager</h2>
        <p className="text-sm text-muted-foreground">Monitor and manage agent task executions</p>
      </div>

      <div className="grid grid-cols-4 gap-4 border-b px-6 py-4">
        {[
          { label: 'Running', count: stats.running, color: 'text-blue-600' },
          { label: 'Queued', count: stats.queued, color: 'text-yellow-600' },
          { label: 'Completed', count: stats.completed, color: 'text-green-600' },
          { label: 'Failed', count: stats.failed, color: 'text-red-600' }
        ].map(s => (
          <button className={cn('rounded-lg border p-3 text-center transition-all', filter === s.label.toLowerCase() ? 'border-primary/50 bg-primary/5' : '')} key={s.label} onClick={() => setFilter(s.label.toLowerCase())} type="button">
            <div className={cn('text-2xl font-bold', s.color)}>{s.count}</div>
            <div className="text-xs text-muted-foreground">{s.label}</div>
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <div className="mx-auto max-w-3xl space-y-2">
          {filtered.length === 0 ? (
            <p className="py-12 text-center text-sm text-muted-foreground">No tasks to display</p>
          ) : (
            filtered.map(task => {
              const cfg = STATUS_CONFIG[task.status] || STATUS_CONFIG.queued

              return (
                <div className={cn('rounded-xl border transition-all', cfg.bg)} key={task.id}>
                  <button className="flex w-full items-center gap-4 p-4 text-left" onClick={() => setExpanded(expanded === task.id ? null : task.id)} type="button">
                    <span className={cn('h-2.5 w-2.5 shrink-0 rounded-full', task.status === 'running' ? 'bg-blue-500 animate-pulse' : task.status === 'completed' ? 'bg-green-500' : task.status === 'failed' ? 'bg-red-500' : 'bg-gray-400')} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium truncate">{task.agentName}</span>
                        <Badge className={cn('text-[10px] h-5', cfg.color)} variant="outline">{cfg.label}</Badge>
                      </div>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        Started {new Date(task.startedAt).toLocaleString()}
                        {task.duration !== null && ` · ${(task.duration / 1000).toFixed(1)}s`}
                      </p>
                    </div>
                    <div className="text-right text-xs text-muted-foreground">
                      <div className="font-mono">{task.inputTokens + task.outputTokens} tokens</div>
                      <div className="font-mono">${task.costUsd.toFixed(4)}</div>
                    </div>
                    {task.status === 'running' && (
                      <Button className="text-destructive" onClick={e => { e.stopPropagation(); updateTask(task.id, { status: 'cancelled' }) }} size="sm" variant="ghost">
                        Cancel
                      </Button>
                    )}
                    <svg className={cn('h-4 w-4 text-muted-foreground transition-transform', expanded === task.id && 'rotate-180')} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                      <path d="M6 9l6 6 6-6" />
                    </svg>
                  </button>

                  {expanded === task.id && (
                    <div className="border-t px-4 py-3">
                      {task.error && (
                        <div className="mb-3 rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
                          {task.error}
                        </div>
                      )}
                      <div className="space-y-1">
                        <p className="text-xs text-muted-foreground">Logs</p>
                        {task.logs.length > 0 ? (
                          <div className="max-h-40 space-y-1 overflow-y-auto rounded-lg bg-muted p-3 font-mono text-xs">
                            {task.logs.map((log, i) => (
                              <div className={cn(
                                log.level === 'error' ? 'text-destructive' :
                                log.level === 'warn' ? 'text-yellow-600' :
                                log.level === 'debug' ? 'text-muted-foreground' : ''
                              )} key={i}>
                                <span className="text-muted-foreground">[{new Date(log.timestamp).toLocaleTimeString()}]</span> {log.message}
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="text-xs text-muted-foreground">No logs available</p>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}
