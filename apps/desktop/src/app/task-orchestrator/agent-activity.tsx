import { useMemo } from 'react'

import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { AgentActivity } from '@/store/task-orchestrator'

interface Props {
  activities: AgentActivity[]
}

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: string }> = {
  idle: { label: 'Idle', color: 'text-gray-500', icon: '○' },
  running: { label: 'Running', color: 'text-blue-500', icon: '▶' },
  thinking: { label: 'Thinking', color: 'text-purple-500', icon: '◉' },
  tool_called: { label: 'Tool Called', color: 'text-orange-500', icon: '⚙' },
  waiting: { label: 'Waiting', color: 'text-yellow-500', icon: '◷' },
  completed: { label: 'Completed', color: 'text-green-500', icon: '✓' },
  failed: { label: 'Failed', color: 'text-red-500', icon: '✗' },
  retrying: { label: 'Retrying', color: 'text-orange-500', icon: '↻' },
}

const ROLE_EMOJIS: Record<string, string> = {
  planner: '📋', developer: '💻', browser: '🌐', research: '🔍',
  writer: '✍️', creative: '🎨', data: '📊', coordinator: '🎯',
  security: '🛡️', qa: '✅', deployment: '🚀', memory: '🧠',
  communication: '📧', review: '👁', coding: '⚡', file: '📁',
}

export function AgentActivityFeed({ activities }: Props) {
  const displayed = useMemo(() => activities.slice(-100).reverse(), [activities])

  const stats = useMemo(() => {
    const running = activities.filter(a => a.status === 'running' || a.status === 'thinking').length
    const completed = activities.filter(a => a.status === 'completed').length
    const failed = activities.filter(a => a.status === 'failed').length

    return { running, completed, failed }
  }, [activities])

  const activeByRole = useMemo(() => {
    const counts: Record<string, number> = {}

    for (const a of activities) {
      if (a.status === 'running' || a.status === 'thinking') {
        counts[a.role] = (counts[a.role] || 0) + 1
      }
    }

    return counts
  }, [activities])

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-4 flex gap-3">
        <MiniStat color="text-blue-500" label="Active" value={stats.running} />
        <MiniStat color="text-green-500" label="Completed" value={stats.completed} />
        <MiniStat color="text-red-500" label="Failed" value={stats.failed} />
      </div>

      {Object.keys(activeByRole).length > 0 && (
        <div className="mb-4 rounded-lg border bg-muted/30 p-3">
          <div className="text-xs text-muted-foreground mb-2">Active Agents by Role</div>
          <div className="flex flex-wrap gap-2">
            {Object.entries(activeByRole).map(([role, count]) => (
              <Badge className="gap-1" key={role} variant="outline">
                <span className="animate-pulse">{ROLE_EMOJIS[role] ?? '🤖'}</span>
                {role} x{count}
              </Badge>
            ))}
          </div>
        </div>
      )}

      <div className="space-y-0.5">
        {displayed.length === 0 ? (
          <p className="py-12 text-center text-sm text-muted-foreground">No agent activity yet</p>
        ) : (
          displayed.map((activity, i) => {
            const cfg = STATUS_CONFIG[activity.status] ?? STATUS_CONFIG.idle

            return (
              <div
                className={cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors',
                  activity.status === 'running' && 'bg-blue-500/5',
                  activity.status === 'failed' && 'bg-red-500/5',
                  activity.status === 'thinking' && 'bg-purple-500/5',
                )}
                key={`${activity.agentId}-${activity.startedAt}-${i}`}
              >
                <span className={cn('w-4 text-center', cfg.color)}>{cfg.icon}</span>

                <span className="text-base shrink-0">{ROLE_EMOJIS[activity.role] ?? '🤖'}</span>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium truncate">{activity.name}</span>
                    <span className={cn('text-xs', cfg.color)}>{cfg.label}</span>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {activity.message || `${activity.role} agent processing task ${activity.taskId.slice(0, 8)}`}
                  </div>
                </div>

                <div className="text-right shrink-0">
                  <div className="text-xs text-muted-foreground font-mono">{activity.model}</div>
                  <div className="text-[10px] text-muted-foreground">{activity.provider}</div>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}

function MiniStat({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="rounded-lg border px-3 py-2 text-center">
      <div className={cn('text-lg font-bold', color)}>{value}</div>
      <div className="text-[10px] text-muted-foreground">{label}</div>
    </div>
  )
}
