import { useStore } from '@nanostores/react'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { $dashboardMetrics } from '@/store/dashboard'
import { $systemStats } from '@/store/system'

function MiniBar({ percent, className }: { percent: number; className?: string }) {
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-(--ui-bg-quaternary)">
      <div
        className={cn('h-full rounded-full transition-all duration-500', className)}
        style={{ width: `${Math.min(percent, 100)}%` }}
      />
    </div>
  )
}

export function SystemMetrics() {
  const metrics = useStore($dashboardMetrics)
  const stats = useStore($systemStats)

  if (!metrics) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>System Resources</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div className="space-y-1.5" key={i}>
                <div className="flex items-center justify-between">
                  <Skeleton className="h-3 w-16" />
                  <Skeleton className="h-3 w-12" />
                </div>
                <Skeleton className="h-1.5 w-full" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  const items = [
    { label: 'CPU', percent: metrics.cpu.current, detail: `${metrics.cpu.current}% avg`, color: 'bg-blue-500' },
    { label: 'Memory', percent: metrics.memory.percent, detail: `${metrics.memory.used.toFixed(1)} GB / ${metrics.memory.total} GB`, color: 'bg-emerald-500' },
    { label: 'Disk', percent: metrics.disk.percent, detail: `${metrics.disk.used} GB / ${metrics.disk.total} GB`, color: 'bg-violet-500' }
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle>System Resources</CardTitle>
        <span className="text-[0.625rem] text-(--ui-text-tertiary)">
          {stats ? `${stats.hostname} • ${stats.platform}` : ''}
        </span>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {items.map(item => (
            <div className="space-y-1.5" key={item.label}>
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium">{item.label}</span>
                <span className="text-xs text-(--ui-text-tertiary)">{item.detail}</span>
              </div>
              <MiniBar className={item.color} percent={item.percent} />
            </div>
          ))}
        </div>
        <div className="mt-4 grid grid-cols-2 gap-2 border-t border-(--ui-stroke-tertiary)/50 pt-3">
          <div>
            <div className="text-[0.625rem] font-medium uppercase tracking-wider text-(--ui-text-tertiary)">Active Sessions</div>
            <div className="mt-0.5 text-sm font-semibold">{metrics.sessions.active} / {metrics.sessions.total}</div>
          </div>
          <div>
            <div className="text-[0.625rem] font-medium uppercase tracking-wider text-(--ui-text-tertiary)">Uptime</div>
            <div className="mt-0.5 text-sm font-semibold">{formatUptime(metrics.uptime)}</div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function formatUptime(startTime: number): string {
  const diff = Date.now() - startTime
  const days = Math.floor(diff / 86400000)
  const hours = Math.floor((diff % 86400000) / 3600000)

  if (days > 0) {return `${days}d ${hours}h`}

  return `${hours}h`
}
