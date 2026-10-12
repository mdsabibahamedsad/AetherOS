import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { Checkpoint } from '@/store/task-orchestrator'

interface Props {
  checkpoints: Checkpoint[]
  planId: string | null
}

export function CheckpointView({ checkpoints, planId }: Props) {
  const planCheckpoints = checkpoints.filter(c => c.planId === planId)

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
          Checkpoints {planId ? `for plan ${planId.slice(0, 8)}` : ''}
        </h3>
        <div className="flex gap-2">
          <Button disabled={!planId} size="sm" variant="outline">Save Checkpoint</Button>
          <Button disabled={planCheckpoints.length === 0} size="sm" variant="outline">Restore Latest</Button>
        </div>
      </div>

      {planCheckpoints.length === 0 ? (
        <div className="flex h-48 items-center justify-center rounded-lg border border-dashed">
          <div className="text-center">
            <p className="text-sm text-muted-foreground">No checkpoints saved yet</p>
            <p className="mt-1 text-xs text-muted-foreground">Checkpoints are created automatically during task execution</p>
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          {planCheckpoints.slice().reverse().map(cp => (
            <div className="flex items-center justify-between rounded-lg border p-3" key={cp.id}>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-green-500" />
                  <span className="text-sm font-medium">Checkpoint {cp.id.slice(0, 8)}</span>
                  <span className="text-xs text-muted-foreground font-mono">task: {cp.taskId.slice(0, 8)}</span>
                </div>
                <div className="mt-1 text-xs text-muted-foreground">
                  {new Date(cp.timestamp * 1000).toLocaleString()}
                  {!!(cp.state as Record<string, unknown>)?.completedTasks && (
                    <> · {Array.isArray((cp.state as Record<string, unknown>).completedTasks) ? ((cp.state as Record<string, unknown>).completedTasks as unknown[]).length : 0} tasks completed</>
                  )}
                </div>
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="ghost">Restore</Button>
                <Button className="text-destructive" size="sm" variant="ghost">Delete</Button>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="mt-8">
        <h4 className="mb-3 text-sm font-semibold text-muted-foreground uppercase tracking-wider">Checkpoint Actions</h4>
        <div className="grid grid-cols-2 gap-3">
          {[
            { label: 'Pause & Save', desc: 'Pause execution and save current state', disabled: false },
            { label: 'Resume from Checkpoint', desc: 'Restore execution from a saved checkpoint', disabled: planCheckpoints.length === 0 },
            { label: 'Cancel Execution', desc: 'Stop all running tasks and save final state', disabled: false },
            { label: 'Restart from Beginning', desc: 'Clear all progress and start over', disabled: false },
          ].map(action => (
            <button
              className={cn(
                'rounded-lg border p-3 text-left transition-colors hover:bg-muted/50',
                action.disabled && 'opacity-40 cursor-not-allowed'
              )}
              disabled={action.disabled}
              key={action.label}
              type="button"
            >
              <div className="text-sm font-medium">{action.label}</div>
              <div className="text-xs text-muted-foreground mt-0.5">{action.desc}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
