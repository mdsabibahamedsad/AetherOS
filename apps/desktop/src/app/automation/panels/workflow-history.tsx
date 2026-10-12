import { useStore } from '@nanostores/react'
import { useState } from 'react'

import { Codicon } from '@/components/ui/codicon'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'
import {
  $automation,
} from '@/store/automation'

export function WorkflowHistory() {
  const state = useStore($automation)
  const workflow = state.workflows.find(w => w.id === state.activeWorkflowId)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [filter, setFilter] = useState<'all' | 'running' | 'completed' | 'failed'>('all')

  const executions = state.executions.filter(e =>
    filter === 'all' ? true : e.status === filter
  )

  if (!workflow) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-(--ui-text-tertiary)">Select a workflow to view execution history</p>
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="flex items-center justify-between border-b border-(--ui-stroke-tertiary) px-6 py-3">
        <div className="flex items-center gap-2">
          <Codicon className="text-blue-400" name="history" size="1rem" />
          <h2 className="text-base font-semibold">Execution History</h2>
        </div>
        <div className="flex items-center gap-1">
          {(['all', 'running', 'completed', 'failed'] as const).map(f => (
            <button
              className={cn(
                'rounded-md px-2.5 py-1 text-xs font-medium transition-colors',
                filter === f
                  ? 'bg-(--ui-control-hover-background) text-foreground'
                  : 'text-(--ui-text-tertiary) hover:text-foreground'
              )}
              key={f}
              onClick={() => setFilter(f)}
              type="button"
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-4 border-b border-(--ui-stroke-tertiary) px-6 py-3">
        {[
          { label: 'Total Runs', value: state.executions.length, color: 'text-(--ui-text-tertiary)' },
          { label: 'Running', value: state.executions.filter(e => e.status === 'running').length, color: 'text-blue-400' },
          { label: 'Completed', value: state.executions.filter(e => e.status === 'completed').length, color: 'text-green-400' },
          { label: 'Failed', value: state.executions.filter(e => e.status === 'failed').length, color: 'text-red-400' },
          { label: 'Avg Duration', value: state.executions.filter(e => e.duration).length > 0
            ? `${Math.round(state.executions.filter(e => e.duration).reduce((a, e) => a + (e.duration ?? 0), 0) / state.executions.filter(e => e.duration).length)}s`
            : '—', color: 'text-(--ui-text-tertiary)' },
        ].map(stat => (
          <div className="text-center" key={stat.label}>
            <div className={cn('text-lg font-semibold tabular-nums', stat.color)}>{stat.value}</div>
            <div className="text-[10px] text-(--ui-text-tertiary)">{stat.label}</div>
          </div>
        ))}
      </div>

      <ScrollArea className="flex-1">
        <div className="space-y-1 p-4">
          {executions.length === 0 && (
            <div className="py-12 text-center">
              <Codicon className="mx-auto mb-3 text-(--ui-text-tertiary)" name="history" size="2rem" />
              <p className="text-sm text-(--ui-text-tertiary)">No execution history yet</p>
              <p className="text-xs text-(--ui-text-tertiary) mt-1">Run the workflow to see results here</p>
            </div>
          )}

          {executions.map(exec => (
            <div className="rounded-xl border border-(--ui-stroke-tertiary) transition-all hover:bg-(--ui-control-hover-background)" key={exec.id}>
              <button
                className="flex w-full items-center gap-4 px-4 py-3"
                onClick={() => setExpandedId(expandedId === exec.id ? null : exec.id)}
                type="button"
              >
                <div className={cn(
                  'flex h-8 w-8 items-center justify-center rounded-lg',
                  exec.status === 'running' ? 'bg-blue-500/10' :
                  exec.status === 'completed' ? 'bg-green-500/10' :
                  exec.status === 'failed' ? 'bg-red-500/10' :
                  'bg-(--ui-stroke-tertiary)'
                )}>
                  <Codicon className={
                    exec.status === 'running' ? 'text-blue-400 animate-spin' :
                    exec.status === 'completed' ? 'text-green-400' :
                    exec.status === 'failed' ? 'text-red-400' :
                    'text-(--ui-text-tertiary)'
                  } name={
                    exec.status === 'running' ? 'sync' :
                    exec.status === 'completed' ? 'check' :
                    exec.status === 'failed' ? 'error' :
                    'circle-slash'
                  } size="1rem" />
                </div>

                <div className="flex-1 min-w-0 text-left">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-foreground">{exec.workflowName}</span>
                    <span className={cn(
                      'rounded-full px-1.5 py-0.5 text-[9px] font-medium',
                      exec.status === 'running' ? 'bg-blue-500/10 text-blue-400' :
                      exec.status === 'completed' ? 'bg-green-500/10 text-green-400' :
                      exec.status === 'failed' ? 'bg-red-500/10 text-red-400' :
                      'bg-(--ui-stroke-tertiary) text-(--ui-text-tertiary)'
                    )}>
                      {exec.status}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-(--ui-text-tertiary)">
                    <span>{new Date(exec.startedAt).toLocaleString()}</span>
                    <span>·</span>
                    <span>{exec.nodesExecuted}/{exec.nodesTotal} nodes</span>
                    {exec.duration && <><span>·</span><span>{exec.duration}s</span></>}
                  </div>
                </div>

                {exec.cost != null && (
                  <span className="text-xs tabular-nums text-(--ui-text-tertiary)">${exec.cost.toFixed(4)}</span>
                )}

                <Codicon className="text-(--ui-text-tertiary)" name={expandedId === exec.id ? 'chevron-up' : 'chevron-down'} size="0.875rem" />
              </button>

              {expandedId === exec.id && (
                <div className="border-t border-(--ui-stroke-tertiary) px-4 py-3 space-y-3">
                  {exec.error && (
                    <div className="rounded-lg bg-red-500/5 px-3 py-2">
                      <p className="text-xs font-medium text-red-400">Error</p>
                      <p className="text-xs text-red-300">{exec.error}</p>
                    </div>
                  )}

                  <div className="grid grid-cols-4 gap-3">
                    {[
                      { label: 'Trigger', value: exec.trigger },
                      { label: 'Retries', value: String(exec.retryCount) },
                      { label: 'Model', value: exec.modelUsed ?? '—' },
                      { label: 'Cost', value: exec.cost != null ? `$${exec.cost.toFixed(4)}` : '—' },
                    ].map(d => (
                      <div className="rounded-lg bg-(--ui-control-hover-background) px-2 py-1.5" key={d.label}>
                        <div className="text-[10px] text-(--ui-text-tertiary)">{d.label}</div>
                        <div className="text-xs font-medium text-foreground truncate">{d.value}</div>
                      </div>
                    ))}
                  </div>

                  {exec.logs.length > 0 && (
                    <div>
                      <p className="mb-1 text-[10px] font-medium text-(--ui-text-tertiary)">Logs</p>
                      <div className="max-h-40 space-y-0.5 overflow-y-auto rounded-lg bg-[#1e1e2e] p-2 font-mono text-[10px]">
                        {exec.logs.map((log, i) => (
                          <div className={cn(
                            'flex items-start gap-2',
                            log.level === 'error' ? 'text-red-400' :
                            log.level === 'warn' ? 'text-amber-400' :
                            log.level === 'debug' ? 'text-(--ui-text-tertiary)' :
                            'text-foreground/80'
                          )} key={i}>
                            <span className="shrink-0 text-(--ui-text-tertiary)">{new Date(log.timestamp).toLocaleTimeString()}</span>
                            <span className="shrink-0 text-[8px] uppercase">{log.level}</span>
                            <span className="break-all">{log.message}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </ScrollArea>
    </div>
  )
}
