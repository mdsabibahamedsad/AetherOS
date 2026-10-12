import { useMemo } from 'react'

import { BrailleSpinner } from '@/components/ui/braille-spinner'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import type { SubagentNode, SubagentStatus } from '@/store/subagents'

export type AgentCardStatus = SubagentStatus | 'idle'

export interface AgentActivitySummary {
  completed: number
  currentTool: string | null
  filesChanged: number
  models: string[]
  tokens: number
  total: number
}

const TERMINAL: ReadonlySet<SubagentStatus> = new Set(['completed', 'failed', 'interrupted'])

/**
 * Roll a subagent tree up into an honest activity summary. Counts come
 * straight from node state — done = terminal nodes, total = all nodes.
 * No estimates, no fabricated progress.
 */
export function summarizeAgentNodes(nodes: SubagentNode[]): AgentActivitySummary {
  const flat: SubagentNode[] = []

  const walk = (list: SubagentNode[]) => {
    for (const node of list) {
      flat.push(node)
      walk(node.children)
    }
  }

  walk(nodes)

  const completed = flat.filter(n => TERMINAL.has(n.status)).length
  const running = flat.find(n => n.status === 'running' || n.status === 'queued')
  const models = [...new Set(flat.map(n => n.model).filter((m): m is string => Boolean(m)))]
  const tokens = flat.reduce((sum, n) => sum + (n.inputTokens ?? 0) + (n.outputTokens ?? 0), 0)
  const filesChanged = flat.reduce((sum, n) => sum + n.filesRead.length + n.filesWritten.length, 0)

  return {
    completed,
    currentTool: running?.currentTool ?? null,
    filesChanged,
    models,
    tokens,
    total: flat.length,
  }
}

const STATUS_META: Record<AgentCardStatus, { dot: string; label: string }> = {
  completed: { dot: 'bg-emerald-500', label: 'Completed' },
  failed: { dot: 'bg-red-500', label: 'Failed' },
  idle: { dot: 'bg-muted-foreground/40', label: 'Idle' },
  interrupted: { dot: 'bg-amber-500', label: 'Stopped' },
  queued: { dot: 'bg-amber-500', label: 'Queued' },
  running: { dot: 'bg-blue-500', label: 'Working' },
}

export interface AgentCardProps {
  className?: string
  /** Last observable activity line (stream summary/tool text), if any. */
  currentActivity?: string | null
  goal?: string | null
  model?: string | null
  nodes: SubagentNode[]
  onInspect?: () => void
  onStop?: () => void
  status: AgentCardStatus
  stopDisabled?: boolean
  title: string
}

/**
 * AGI-style agent card: identity, goal, concise status summary, progress,
 * tools/model/tokens/files, and Inspect/Stop actions. Shows observable
 * actions and summaries only — never raw chain-of-thought. Every number
 * derives from the provided nodes via summarizeAgentNodes.
 */
export function AgentCard({
  className,
  currentActivity,
  goal,
  model,
  nodes,
  onInspect,
  onStop,
  status,
  stopDisabled,
  title,
}: AgentCardProps) {
  const summary = useMemo(() => summarizeAgentNodes(nodes), [nodes])
  const meta = STATUS_META[status]
  const live = status === 'running' || status === 'queued'
  const progress = summary.total > 0 ? Math.round((summary.completed / summary.total) * 100) : 0

  const facts = [
    summary.currentTool ? `Using ${summary.currentTool}` : '',
    model ? `Model ${model}` : '',
    summary.tokens > 0 ? `${summary.tokens.toLocaleString()} tokens` : '',
    summary.filesChanged > 0 ? `${summary.filesChanged} files touched` : '',
  ].filter(Boolean)

  return (
    <Card className={cn('p-4', className)} data-testid="agent-card">
      <div className="flex items-start gap-3">
        {live ? (
          <BrailleSpinner
            ariaLabel={meta.label}
            className="mt-0.5 size-4 shrink-0 text-muted-foreground/80"
            spinner="breathe"
          />
        ) : (
          <span aria-hidden className={cn('mt-1.5 size-2.5 shrink-0 rounded-full', meta.dot)} />
        )}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
            <h3 className="truncate text-sm font-semibold tracking-tight">{title}</h3>
            <span aria-label={`${meta.label}, ${summary.completed} of ${summary.total} steps`} className="text-xs text-muted-foreground" role="status">
              {meta.label}
              {summary.total > 0 ? ` · ${summary.completed}/${summary.total} steps` : ''}
            </span>
          </div>
          {goal ? <p className="mt-0.5 truncate text-xs text-muted-foreground">{goal}</p> : null}
          {currentActivity ? (
            <p className="mt-1 truncate font-mono text-[0.7rem] text-foreground/80">{currentActivity}</p>
          ) : null}

          {summary.total > 0 ? (
            <div
              aria-label={`Progress ${progress} percent`}
              aria-valuemax={100}
              aria-valuemin={0}
              aria-valuenow={progress}
              className="mt-2 h-1 overflow-hidden rounded-full bg-(--ui-bg-tertiary)"
              role="progressbar"
            >
              <div
                className={cn('h-full rounded-full transition-all', live ? 'bg-blue-500' : 'bg-emerald-500')}
                style={{ width: `${progress}%` }}
              />
            </div>
          ) : null}

          {facts.length > 0 ? (
            <p className="mt-1.5 truncate text-[0.68rem] text-muted-foreground/75">{facts.join(' · ')}</p>
          ) : null}
        </div>

        <div className="flex shrink-0 items-center gap-1.5">
          {onInspect ? (
            <Button onClick={onInspect} size="sm" variant="outline">
              Inspect
            </Button>
          ) : null}
          {onStop && live ? (
            <Button
              disabled={stopDisabled}
              onClick={onStop}
              size="sm"
              title={stopDisabled ? 'Unavailable while offline' : 'Interrupt this agent'}
              variant="outline"
            >
              Stop
            </Button>
          ) : null}
        </div>
      </div>
    </Card>
  )
}
