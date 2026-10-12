import { useStore } from '@nanostores/react'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { $activityFeed } from '@/store/dashboard'

const TYPE_ICONS: Record<string, string> = {
  backup: 'codicon-cloud-download',
  update: 'codicon-sync',
  health: 'codicon-heart',
  install: 'codicon-package',
  system: 'codicon-settings-gear'
}

const STATUS_COLORS: Record<string, string> = {
  info: 'text-blue-500',
  success: 'text-emerald-500',
  warning: 'text-amber-500',
  error: 'text-red-500'
}

export function ActivityFeed() {
  const events = useStore($activityFeed)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Activity</CardTitle>
        {events.length > 0 && (
          <span className="text-[0.625rem] text-(--ui-text-tertiary)">{events.length} events</span>
        )}
      </CardHeader>
      <CardContent>
        {events.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-(--ui-text-tertiary)">
            <span className="codicon codicon-inbox text-2xl" />
            <p className="mt-2 text-xs">No recent activity</p>
          </div>
        ) : (
          <div className="space-y-1">
            {events.map(event => (
              <div
                className="flex items-start gap-3 rounded-lg px-3 py-2 transition-colors hover:bg-(--ui-control-hover-background)"
                key={event.id}
              >
                <span className={cn('codicon mt-0.5 text-sm', TYPE_ICONS[event.type] || 'codicon-circle', STATUS_COLORS[event.status])} />
                <div className="min-w-0 flex-1">
                  <div className="text-sm">{event.message}</div>
                  <div className="text-[0.625rem] text-(--ui-text-tertiary)">{formatRelativeTime(event.timestamp)}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function formatRelativeTime(ts: number): string {
  const diff = Date.now() - ts

  if (diff < 60000) {return 'just now'}

  if (diff < 3600000) {return `${Math.floor(diff / 60000)}m ago`}

  if (diff < 86400000) {return `${Math.floor(diff / 3600000)}h ago`}

  return `${Math.floor(diff / 86400000)}d ago`
}
