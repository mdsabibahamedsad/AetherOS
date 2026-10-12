import { useMemo } from 'react'

import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { ExecutionState, OrchestrationPlan } from '@/store/task-orchestrator'

interface Props {
  plan: OrchestrationPlan | null
  executionState: ExecutionState | null
}

const ROLE_COLORS: Record<string, string> = {
  planner: 'bg-purple-500/10 text-purple-600 border-purple-500/30',
  developer: 'bg-blue-500/10 text-blue-600 border-blue-500/30',
  research: 'bg-teal-500/10 text-teal-600 border-teal-500/30',
  writer: 'bg-green-500/10 text-green-600 border-green-500/30',
  browser: 'bg-cyan-500/10 text-cyan-600 border-cyan-500/30',
  qa: 'bg-orange-500/10 text-orange-600 border-orange-500/30',
  deployment: 'bg-red-500/10 text-red-600 border-red-500/30',
  security: 'bg-rose-500/10 text-rose-600 border-rose-500/30',
  creative: 'bg-pink-500/10 text-pink-600 border-pink-500/30',
  data: 'bg-amber-500/10 text-amber-600 border-amber-500/30',
  communication: 'bg-indigo-500/10 text-indigo-600 border-indigo-500/30',
  review: 'bg-violet-500/10 text-violet-600 border-violet-500/30',
  coordinator: 'bg-primary/10 text-primary border-primary/30',
}

export function PlanView({ plan, executionState }: Props) {
  const completedSet = useMemo(() => new Set(executionState?.completedTasks ?? []), [executionState])
  const failedSet = useMemo(() => new Set(executionState?.failedTasks ?? []), [executionState])
  const runningSet = useMemo(() => new Set(executionState?.runningTasks ?? []), [executionState])

  if (!plan) {
    return (
      <div className="flex h-48 items-center justify-center">
        <p className="text-sm text-muted-foreground">Select or create a plan to view details</p>
      </div>
    )
  }

  const completedCount = completedSet.size
  const failedCount = failedSet.size
  const runningCount = runningSet.size
  const totalCount = plan.subtasks.length
  const progress = totalCount > 0 ? Math.round(((completedCount + failedCount) / totalCount) * 100) : 0

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div className="rounded-lg border p-4">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h3 className="font-semibold">{plan.goal.slice(0, 120)}</h3>
            <p className="mt-1 text-xs text-muted-foreground">{plan.description.slice(0, 200)}</p>
          </div>
          <RiskBadge level={plan.riskLevel} />
        </div>

        <div className="mt-4 grid grid-cols-4 gap-3">
          <Metric label="Tasks" value={String(totalCount)} />
          <Metric label="Est. Time" value={`${Math.round(plan.estimatedTime)}s`} />
          <Metric label="Est. Cost" value={`$${plan.estimatedCost.toFixed(2)}`} />
          <Metric label="Progress" value={`${progress}%`} />
        </div>

        {totalCount > 0 && (
          <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-green-500 transition-all"
              style={{ width: `${(completedCount / totalCount) * 100}%` }}
            />
          </div>
        )}

        <div className="mt-3 flex gap-4 text-xs text-muted-foreground">
          <span>{completedCount} completed</span>
          <span className="text-blue-500">{runningCount} running</span>
          {failedCount > 0 && <span className="text-red-500">{failedCount} failed</span>}
          <span>{totalCount - completedCount - runningCount - failedCount} pending</span>
        </div>
      </div>

      <div className="space-y-2">
        <h4 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Tasks</h4>
        {plan.subtasks.map((task, idx) => {
          const isCompleted = completedSet.has(task.id)
          const isFailed = failedSet.has(task.id)
          const isRunning = runningSet.has(task.id)
          const status = isCompleted ? 'completed' : isFailed ? 'failed' : isRunning ? 'running' : 'pending'

          return (
            <div
              className={cn(
                'rounded-lg border p-3 transition-all',
                isCompleted && 'border-green-500/30 bg-green-500/5',
                isRunning && 'border-blue-500/30 bg-blue-500/5',
                isFailed && 'border-red-500/30 bg-red-500/5',
              )}
              key={task.id}
            >
              <div className="flex items-start gap-3">
                <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-medium text-muted-foreground">
                  {idx + 1}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <StatusDot status={status} />
                    <span className={cn('font-medium text-sm', isCompleted && 'line-through text-muted-foreground')}>
                      {task.name}
                    </span>
                    <Badge className={cn('text-[10px] h-5', ROLE_COLORS[task.agentRole] ?? '')} variant="outline">
                      {task.agentRole}
                    </Badge>
                    {task.requiresApproval && (
                      <Badge className="text-[10px] h-5 text-yellow-600 border-yellow-500/30 bg-yellow-500/10" variant="outline">
                        approval
                      </Badge>
                    )}
                  </div>

                  <p className="mt-0.5 text-xs text-muted-foreground">{task.description.slice(0, 120)}</p>

                  <div className="mt-1.5 flex flex-wrap items-center gap-2 text-[10px] text-muted-foreground">
                    {task.tools.length > 0 && (
                      <span>Tools: {task.tools.join(', ')}</span>
                    )}
                    <span>Est: {task.estimatedDuration}s</span>
                    {task.retryCount > 0 && (
                      <span className="text-orange-500">Retries: {task.retryCount}/{task.maxRetries}</span>
                    )}
                  </div>

                  {isRunning && task.progress > 0 && (
                    <div className="mt-2 h-1 w-32 overflow-hidden rounded-full bg-muted">
                      <div className="h-full rounded-full bg-blue-500 transition-all" style={{ width: `${task.progress}%` }} />
                    </div>
                  )}

                  {isFailed && task.error && (
                    <p className="mt-1 text-xs text-red-500">{task.error.slice(0, 200)}</p>
                  )}
                </div>

                {task.dependencies.length > 0 && (
                  <div className="shrink-0 text-[10px] text-muted-foreground">
                    <span className="font-mono">after: {task.dependencies.length}</span>
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border bg-muted/30 px-3 py-2 text-center">
      <div className="text-lg font-bold">{value}</div>
      <div className="text-[10px] text-muted-foreground">{label}</div>
    </div>
  )
}

function StatusDot({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending: 'bg-gray-400', running: 'bg-blue-500 animate-pulse', completed: 'bg-green-500',
    failed: 'bg-red-500', cancelled: 'bg-gray-400', paused: 'bg-yellow-500'
  }

  return <span className={cn('h-2 w-2 shrink-0 rounded-full', colors[status] ?? 'bg-gray-400')} />
}

function RiskBadge({ level }: { level: string }) {
  const colors: Record<string, string> = {
    low: 'bg-green-500/10 text-green-600 border-green-500/30',
    medium: 'bg-yellow-500/10 text-yellow-600 border-yellow-500/30',
    high: 'bg-orange-500/10 text-orange-600 border-orange-500/30',
    critical: 'bg-red-500/10 text-red-600 border-red-500/30'
  }

  return <Badge className={cn(colors[level] ?? '')} variant="outline">{level}</Badge>
}
