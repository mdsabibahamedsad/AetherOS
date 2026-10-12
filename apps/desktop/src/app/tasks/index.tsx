import { useStore } from '@nanostores/react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { deleteCronJob, pauseCronJob, resumeCronJob, triggerCronJob } from '@/aetheros'
import { jobState } from '@/app/cron/job-state'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { EmptyState } from '@/components/ui/empty-state'
import { ScrollArea } from '@/components/ui/scroll-area'
import { StatusDot } from '@/components/ui/status-dot'
import { Table } from '@/components/ui/table'
import { TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { formatTimestamp } from '@/lib/format-timestamp'
import { cn } from '@/lib/utils'
import { $desktopActionTasks } from '@/store/activity'
import { $cronJobs, updateCronJobs } from '@/store/cron'
import { notify, notifyError } from '@/store/notifications'

export interface TaskRow {
  agent: string
  createdAt: number
  /** Raw cron job id (cron rows only) — the handle for lifecycle actions. */
  cronId: string | null
  description: string
  id: string
  lastRun: number | string | null
  /** Effective paused state (cron rows only), via the shared jobState rule. */
  paused: boolean
  status: string
  title: string
  type: 'action' | 'cron'
}

export type TaskRowAction = 'delete' | 'pause' | 'resume' | 'trigger' | 'view'

/**
 * Actions a row supports. Cron rows expose the real lifecycle methods the
 * runtime provides (pause/resume/trigger/delete); desktop-action rows have
 * no stop endpoint, so they stay view-only rather than faking a control.
 */
export function getTaskRowActions(task: Pick<TaskRow, 'status' | 'type'>): TaskRowAction[] {
  if (task.type === 'cron') {
    const terminated = task.status === 'completed' || task.status === 'cancelled' || task.status === 'error' || task.status === 'failed'

    return terminated ? ['view', 'delete'] : ['pause', 'trigger', 'view', 'delete']
  }

  return ['view']
}

/** Resolve pause vs resume from the row's paused flag (shared jobState rule). */
export function pauseResumeAction(paused: boolean): 'pause' | 'resume' {
  return paused ? 'resume' : 'pause'
}

/** Active = anything not settled. Settled ids are computed from the completed
 *  + failed partitions so a terminal status (e.g. `success`) can never appear
 *  in both Active and Completed. */
export function partitionActiveTasks<T extends { id: string }>(allTasks: T[], settledIds: Set<string>): T[] {
  return allTasks.filter(t => !settledIds.has(t.id))
}

export function TasksView() {
  const navigate = useNavigate()
  const cronJobs = useStore($cronJobs)
  const actionTasks = useStore($desktopActionTasks)

  // Collect all tasks from both sources
  const allTasks: TaskRow[] = [
    ...cronJobs.map((job: any) => ({
      id: `cron:${job.id}`,
      title: job.title || 'Unnamed Cron Job',
      description: job.schedule || 'Scheduled job',
      status: job.status || 'pending',
      type: 'cron' as const,
      createdAt: job.createdAt || Date.now(),
      lastRun: job.nextRun || null,
      agent: job.agent || 'System',
      cronId: String(job.id),
      paused: jobState(job) === 'paused',
    })),
    ...Object.entries(actionTasks).map(([key, task]: [string, any]) => ({
      id: `action:${key}`,
      title: task.status.name || 'Action',
      description: task.status.description || '',
      status: task.status.running ? 'running' : task.status.exit_code === 0 ? 'success' : 'error',
      type: 'action' as const,
      createdAt: task.updatedAt || Date.now(),
      lastRun: task.updatedAt || null,
      agent: 'Agent',
      cronId: null,
      paused: false,
    })),
  ]

  // Sort by creation date, newest first
  allTasks.sort((a, b) => b.createdAt - a.createdAt)

  const completedTasks = allTasks.filter(t => t.status === 'completed' || t.status === 'success')
  const failedTasks = allTasks.filter(t => t.status === 'error' || t.status === 'failed')
  const settledIds = new Set([...completedTasks, ...failedTasks].map(t => t.id))
  const activeTasks = partitionActiveTasks(allTasks, settledIds)

  type TaskFilter = 'active' | 'completed' | 'failed' | 'all'
  const [filter, setFilter] = useState<TaskFilter>('all')

  const visibleTasks =
    filter === 'active'
      ? activeTasks
      : filter === 'completed'
        ? completedTasks
        : filter === 'failed'
          ? failedTasks
          : allTasks

  // Per-row busy marker so a slow lifecycle call disables only its own row.
  // Lifecycle methods mirror the Cron overlay's established pattern: apply
  // the returned job to $cronJobs, toast success, toast + preserve on error.
  const [busyTaskId, setBusyTaskId] = useState<string | null>(null)

  const handlePauseResume = async (task: TaskRow) => {
    if (!task.cronId) {
      return
    }

    setBusyTaskId(task.id)

    try {
      const updated = task.paused ? await resumeCronJob(task.cronId) : await pauseCronJob(task.cronId)
      updateCronJobs(rows => rows.map(row => (String(row.id) === task.cronId ? updated : row)))
      notify({ kind: 'success', title: task.paused ? 'Task resumed' : 'Task paused', message: task.title })
    } catch (err) {
      notifyError(err, `Failed to ${task.paused ? 'resume' : 'pause'} ${task.title} — change not saved`)
    } finally {
      setBusyTaskId(null)
    }
  }

  const handleTrigger = async (task: TaskRow) => {
    if (!task.cronId) {
      return
    }

    setBusyTaskId(task.id)

    try {
      const updated = await triggerCronJob(task.cronId)
      updateCronJobs(rows => rows.map(row => (String(row.id) === task.cronId ? updated : row)))
      notify({ kind: 'success', title: 'Task triggered', message: task.title })
    } catch (err) {
      notifyError(err, `Failed to trigger ${task.title}`)
    } finally {
      setBusyTaskId(null)
    }
  }

  const handleDelete = async (task: TaskRow) => {
    if (!task.cronId) {
      return
    }

    if (!window.confirm(`Delete this scheduled task?\n\n${task.title}\n\nThis cannot be undone.`)) {
      return
    }

    setBusyTaskId(task.id)

    try {
      await deleteCronJob(task.cronId)
      updateCronJobs(rows => rows.filter(row => String(row.id) !== task.cronId))
      notify({ kind: 'success', title: 'Task deleted', message: task.title })
    } catch (err) {
      notifyError(err, `Failed to delete ${task.title} — change not saved`)
    } finally {
      setBusyTaskId(null)
    }
  }

  return (
    <ScrollArea className="h-full">
      <div className="mx-auto max-w-7xl space-y-6 p-6">
        <Card className="p-6">
          <h2 className="text-2xl font-semibold tracking-tight">Tasks</h2>
          <p className="text-(--ui-text-tertiary) mb-4">Background and scheduled tasks</p>

          <div className="grid gap-4 mb-6 sm:grid-cols-3">
            <TaskSummaryCard
              active={filter === 'active'}
              count={activeTasks.length}
              label="Active"
              onSelect={() => setFilter(filter === 'active' ? 'all' : 'active')}
              status="running"
            />
            <TaskSummaryCard
              active={filter === 'completed'}
              count={completedTasks.length}
              label="Completed"
              onSelect={() => setFilter(filter === 'completed' ? 'all' : 'completed')}
              status="success"
            />
            <TaskSummaryCard
              active={filter === 'failed'}
              count={failedTasks.length}
              label="Failed"
              onSelect={() => setFilter(filter === 'failed' ? 'all' : 'failed')}
              status="error"
            />
          </div>

          {allTasks.length === 0 ? (
            <EmptyState
              description="Scheduled and background tasks will appear here"
              icon="checklist"
              title="No active tasks"
            />
          ) : (
          <>
          <p className="mb-2 text-xs text-(--ui-text-tertiary)" role="status">
            Showing {Math.min(visibleTasks.length, 20)} of {visibleTasks.length} task{visibleTasks.length === 1 ? '' : 's'}
            {filter !== 'all' ? ` · filtered by ${filter} — select again to clear` : ''}
          </p>
          <Table>
            <TableHead>
              <TableRow>
                <TableHeader>Task</TableHeader>
                <TableHeader>Status</TableHeader>
                <TableHeader>Type</TableHeader>
                <TableHeader>Created</TableHeader>
                <TableHeader>Last Run</TableHeader>
                <TableHeader>Actions</TableHeader>
              </TableRow>
            </TableHead>
            <TableBody>
              {visibleTasks.length === 0 ? (
                <TableRow>
                  <TableCell className="py-6 text-center text-sm text-(--ui-text-tertiary)" colSpan={6}>
                    No {filter} tasks — select the filter again to show all tasks.
                  </TableCell>
                </TableRow>
              ) : null}
              {visibleTasks.slice(0, 20).map((task: TaskRow) => {
                const actions = getTaskRowActions(task)
                const pauseResume = pauseResumeAction(task.paused)

                return (
                  <TableRow key={task.id}>
                    <TableCell className="font-medium">
                      <div className="truncate max-w-xs">{task.title}</div>
                      {task.description && (
                        <div className="text-xs text-(--ui-text-tertiary) truncate">
                          {task.description}
                        </div>
                      )}
                    </TableCell>
                    <TableCell>
                      <StatusDot size="sm" status={task.status} />
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{task.type}</Badge>
                    </TableCell>
                    <TableCell>
                      <div className="text-xs text-(--ui-text-tertiary)">{formatTimestamp(task.createdAt)}</div>
                    </TableCell>
                    <TableCell>
                      {task.lastRun ? (
                        <div className="text-xs text-(--ui-text-tertiary)">{formatTimestamp(task.lastRun)}</div>
                      ) : (
                        <div className="text-xs text-(--ui-text-tertiary)">—</div>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-0.5">
                        {actions.includes(pauseResume) && (
                          <Button
                            aria-label={task.paused ? `Resume ${task.title}` : `Pause ${task.title}`}
                            className="p-1.5 rounded hover:bg-(--ui-surface-hover)"
                            disabled={busyTaskId === task.id}
                            onClick={() => void handlePauseResume(task)}
                            size="icon"
                            title={task.paused ? 'Resume schedule' : 'Pause schedule'}
                          >
                            <span className={`codicon ${task.paused ? 'codicon-debug-start' : 'codicon-debug-pause'}`} />
                          </Button>
                        )}
                        {actions.includes('trigger') && (
                          <Button
                            aria-label={`Run ${task.title} now`}
                            className="p-1.5 rounded hover:bg-(--ui-surface-hover)"
                            disabled={busyTaskId === task.id}
                            onClick={() => void handleTrigger(task)}
                            size="icon"
                            title="Run now"
                          >
                            <span className="codicon codicon-play" />
                          </Button>
                        )}
                        <Button
                          aria-label={`View ${task.title} details`}
                          className="p-1.5 rounded hover:bg-(--ui-surface-hover)"
                          onClick={() => navigate(task.type === 'cron' ? '/automation-center' : '/task-orchestrator')}
                          size="icon"
                          title="View details"
                        >
                          <span className="codicon codicon-eye" />
                        </Button>
                        {actions.includes('delete') && (
                          <Button
                            aria-label={`Delete ${task.title}`}
                            className="p-1.5 rounded hover:bg-(--ui-surface-hover)"
                            disabled={busyTaskId === task.id}
                            onClick={() => void handleDelete(task)}
                            size="icon"
                            title="Delete scheduled task"
                          >
                            <span className="codicon codicon-trash" />
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
          </>
          )}
        </Card>
      </div>
    </ScrollArea>
  )
}

interface TaskSummaryCardProps {
  active?: boolean
  label: string
  count: number
  onSelect?: () => void
  status: 'running' | 'success' | 'error'
}

function TaskSummaryCard({ active, label, count, onSelect, status }: TaskSummaryCardProps) {
  const colors = {
    running: 'from-blue-500/20 to-blue-600/10 border-blue-500/20',
    success: 'from-emerald-500/20 to-emerald-600/10 border-emerald-500/20',
    error: 'from-red-500/20 to-red-600/10 border-red-500/20',
  }

  return (
    <Card
      className={cn(
        'p-4 rounded-xl border',
        colors[status]
      )}
    >
      <button
        aria-pressed={Boolean(active)}
        className="flex w-full items-center justify-between text-left"
        onClick={onSelect}
        type="button"
      >
        <span className="text-sm font-medium">
          {label}
          {active ? <span className="ml-2 text-xs text-(--ui-text-tertiary)">●</span> : null}
        </span>
        <span className="text-2xl font-bold text-(--ui-text)">{count}</span>
      </button>
    </Card>
  )
}