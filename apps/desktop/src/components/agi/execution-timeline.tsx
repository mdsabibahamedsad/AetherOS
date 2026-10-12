import { useMemo } from 'react'

import { AGENT_LIFECYCLE_LABEL, agentLifecycleFromSubagent } from '@/lib/agi-states'
import { cn } from '@/lib/utils'
import type { SubagentNode } from '@/store/subagents'

export interface TimelineEvent {
  /** Epoch ms. Events without timestamps are dropped, never guessed. */
  at: number
  id: string
  label: string
  tone: 'good' | 'bad' | 'warn' | 'muted' | 'info'
}

/**
 * Derive an operational execution timeline from subagent node lifecycles:
 * one "started" event per node (goal as label) plus one terminal event
 * (completed/failed/cancelled with summary when present). Stream chatter
 * is excluded — this is history, not a transcript.
 */
export function nodeTimelineEvents(nodes: SubagentNode[]): TimelineEvent[] {
  const flat: SubagentNode[] = []

  const walk = (list: SubagentNode[]) => {
    for (const node of list) {
      flat.push(node)
      walk(node.children)
    }
  }

  walk(nodes)

  const events: TimelineEvent[] = []

  for (const node of flat) {
    if (typeof node.startedAt === 'number' && node.startedAt > 0) {
      events.push({
        at: node.startedAt,
        id: `${node.id}:started`,
        label: `Started — ${node.goal || node.id}`,
        tone: 'info',
      })
    }

    const lifecycle = agentLifecycleFromSubagent(node.status)

    if ((lifecycle === 'completed' || lifecycle === 'failed' || lifecycle === 'cancelled') && node.updatedAt > 0) {
      events.push({
        at: node.updatedAt,
        id: `${node.id}:terminal`,
        label: `${AGENT_LIFECYCLE_LABEL[lifecycle]}${node.summary ? ` — ${node.summary}` : ''}`,
        tone: lifecycle === 'completed' ? 'good' : lifecycle === 'failed' ? 'bad' : 'warn',
      })
    }
  }

  return events.sort((a, b) => a.at - b.at)
}

const TONE_DOT: Record<TimelineEvent['tone'], string> = {
  good: 'bg-emerald-500',
  bad: 'bg-red-500',
  warn: 'bg-amber-500',
  muted: 'bg-muted-foreground/40',
  info: 'bg-blue-500',
}

function formatTime(at: number): string {
  return new Date(at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export function ExecutionTimeline({ className, nodes }: { className?: string; nodes: SubagentNode[] }) {
  const events = useMemo(() => nodeTimelineEvents(nodes), [nodes])

  if (events.length === 0) {
    return null
  }

  return (
    <section aria-label="Execution timeline" className={cn('min-w-0', className)} data-testid="execution-timeline">
      <p className="text-[0.66rem] font-semibold uppercase tracking-wider text-muted-foreground/70">
        Execution timeline
      </p>
      <ol className="mt-2 grid gap-0">
        {events.map((event, index) => (
          <li className="flex min-w-0 gap-2.5" key={event.id}>
            <span aria-hidden className="flex flex-col items-center">
              <span className={cn('mt-1.5 size-2 shrink-0 rounded-full', TONE_DOT[event.tone])} />
              {index < events.length - 1 ? <span className="w-px flex-1 bg-border" /> : null}
            </span>
            <div className="min-w-0 flex-1 pb-3">
              <p className="truncate text-[0.76rem] text-foreground/90">{event.label}</p>
              <p className="font-mono text-[0.64rem] text-muted-foreground/70">{formatTime(event.at)}</p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  )
}
