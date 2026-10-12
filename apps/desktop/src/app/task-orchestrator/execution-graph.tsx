import { useMemo } from 'react'

import { cn } from '@/lib/utils'
import type { ExecutionState, OrchestrationPlan } from '@/store/task-orchestrator'

interface Props {
  plan: OrchestrationPlan | null
  executionState: ExecutionState | null
}

export function ExecutionGraphView({ plan, executionState }: Props) {
  const taskMap = useMemo(() => {
    const map = new Map((plan?.subtasks ?? []).map(t => [t.id, t]))

    return map
  }, [plan?.subtasks])

  if (!plan) {
    return (
      <div className="flex h-48 items-center justify-center">
        <p className="text-sm text-muted-foreground">Select a plan to view its execution graph</p>
      </div>
    )
  }

  const { levels, edges } = plan.executionGraph

  const completedSet = new Set(executionState?.completedTasks ?? [])
  const failedSet = new Set(executionState?.failedTasks ?? [])
  const runningSet = new Set(executionState?.runningTasks ?? [])
  const pendingSet = new Set(executionState?.pendingTasks ?? [])

  const getTaskStatus = (taskId: string): string => {
    if (completedSet.has(taskId)) {return 'completed'}

    if (failedSet.has(taskId)) {return 'failed'}

    if (runningSet.has(taskId)) {return 'running'}

    if (pendingSet.has(taskId)) {return 'pending'}

    return 'pending'
  }

  return (
    <div className="mx-auto max-w-4xl">
      <h3 className="mb-4 text-sm font-semibold text-muted-foreground uppercase tracking-wider">Execution Graph</h3>

      <div className="space-y-6">
        {levels.map((level, levelIdx) => (
          <div key={levelIdx}>
            <div className="mb-2 text-xs text-muted-foreground font-mono">Level {levelIdx + 1}</div>
            <div className={cn('flex gap-3', level.length > 1 ? 'flex-wrap' : '')}>
              {level.map(taskId => {
                const task = taskMap.get(taskId)

                if (!task) {return null}
                const status = getTaskStatus(taskId)

                return (
                  <div
                    className={cn(
                      'relative flex flex-col rounded-lg border p-3 min-w-[180px] max-w-[220px] transition-all',
                      status === 'completed' && 'border-green-500/30 bg-green-500/5',
                      status === 'running' && 'border-blue-500/50 bg-blue-500/10 ring-1 ring-blue-500/30',
                      status === 'failed' && 'border-red-500/30 bg-red-500/5',
                      status === 'pending' && 'border-muted bg-muted/30',
                    )}
                    key={taskId}
                  >
                    <div className="flex items-center gap-2">
                      <span className={cn(
                        'h-2 w-2 shrink-0 rounded-full',
                        status === 'completed' && 'bg-green-500',
                        status === 'running' && 'bg-blue-500 animate-pulse',
                        status === 'failed' && 'bg-red-500',
                        status === 'pending' && 'bg-gray-400',
                      )} />
                      <span className="text-xs font-medium truncate">{task.name}</span>
                    </div>

                    <div className="mt-1.5 flex items-center gap-2 text-[10px] text-muted-foreground">
                      <Badge role={task.agentRole} />
                      <ModeBadge mode={task.executionMode} />
                    </div>

                    {status === 'running' && task.progress > 0 && (
                      <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-muted">
                        <div className="h-full rounded-full bg-blue-500 transition-all" style={{ width: `${task.progress}%` }} />
                      </div>
                    )}
                  </div>
                )
              })}
            </div>

            {levelIdx < levels.length - 1 && (
              <div className="flex justify-center py-2">
                <svg className="h-5 w-5 text-muted-foreground" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path d="M12 5v14M5 12l7 7 7-7" />
                </svg>
              </div>
            )}
          </div>
        ))}
      </div>

      {edges.length > 0 && (
        <div className="mt-8">
          <h4 className="mb-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Dependencies</h4>
          <div className="space-y-1">
            {edges.map((edge, i) => {
              const fromTask = taskMap.get(edge.from)
              const toTask = taskMap.get(edge.to)

              return (
                <div className="flex items-center gap-2 text-xs text-muted-foreground" key={i}>
                  <span className="font-medium text-foreground">{fromTask?.name ?? edge.from}</span>
                  <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                    <path d="M5 12h14M12 5l7 7-7 7" />
                  </svg>
                  <span className="font-medium text-foreground">{toTask?.name ?? edge.to}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      <div className="mt-8">
        <h4 className="mb-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Legend</h4>
        <div className="flex flex-wrap gap-4">
          {[
            { color: 'bg-green-500', label: 'Completed' },
            { color: 'bg-blue-500', label: 'Running' },
            { color: 'bg-red-500', label: 'Failed' },
            { color: 'bg-gray-400', label: 'Pending' },
          ].map(item => (
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground" key={item.label}>
              <span className={cn('h-2 w-2 rounded-full', item.color)} />
              {item.label}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function Badge({ role }: { role: string }) {
  const colors: Record<string, string> = {
    planner: 'bg-purple-500/10 text-purple-600',
    developer: 'bg-blue-500/10 text-blue-600',
    research: 'bg-teal-500/10 text-teal-600',
    writer: 'bg-green-500/10 text-green-600',
    creative: 'bg-pink-500/10 text-pink-600',
    data: 'bg-orange-500/10 text-orange-600',
    coordinator: 'bg-primary/10 text-primary',
    security: 'bg-red-500/10 text-red-600',
    browser: 'bg-cyan-500/10 text-cyan-600',
  }

  return <span className={cn('rounded px-1 py-0.5 font-mono text-[10px]', colors[role] ?? 'bg-muted text-muted-foreground')}>{role}</span>
}

function ModeBadge({ mode }: { mode: string }) {
  if (mode === 'sequential') {return null}

  return <span className="rounded bg-yellow-500/10 px-1 py-0.5 font-mono text-[10px] text-yellow-600">{mode}</span>
}
