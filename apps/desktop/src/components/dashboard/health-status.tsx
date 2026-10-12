import { useStore } from '@nanostores/react'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { $healthChecks } from '@/store/dashboard'

const STATUS_ICONS: Record<string, string> = {
  passed: 'codicon-check text-emerald-500',
  warning: 'codicon-warning text-amber-500',
  failed: 'codicon-error text-red-500'
}

const STATUS_LABELS: Record<string, string> = {
  passed: 'Passed',
  warning: 'Warning',
  failed: 'Failed'
}

export function HealthStatus() {
  const checks = useStore($healthChecks)

  if (!checks || checks.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Health Checks</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton className="h-10 w-full" key={i} />
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  const passed = checks.filter(c => c.status === 'passed').length
  const warning = checks.filter(c => c.status === 'warning').length
  const failed = checks.filter(c => c.status === 'failed').length

  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle>Health Checks</CardTitle>
          <CardDescription>{checks.length} checks • {passed} passed • {warning} warnings • {failed} failed</CardDescription>
        </div>
        <div className={cn(
          'flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[0.625rem] font-semibold uppercase tracking-wider',
          failed > 0 ? 'bg-red-500/10 text-red-500' : warning > 0 ? 'bg-amber-500/10 text-amber-500' : 'bg-emerald-500/10 text-emerald-500'
        )}>
          <span className={cn(
            'codicon text-xs',
            failed > 0 ? 'codicon-error' : warning > 0 ? 'codicon-warning' : 'codicon-check'
          )} />
          {failed > 0 ? 'Degraded' : warning > 0 ? 'Degraded' : 'Healthy'}
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-1">
          {checks.map(check => (
            <div
              className="flex items-center gap-3 rounded-lg px-3 py-2 transition-colors hover:bg-(--ui-control-hover-background)"
              key={check.id}
            >
              <span className={STATUS_ICONS[check.status] || 'codicon-circle text-(--ui-text-tertiary)'} />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{check.name}</span>
                  <Badge variant={check.status === 'passed' ? 'default' : check.status === 'warning' ? 'warn' : 'destructive'}>
                    {STATUS_LABELS[check.status]}
                  </Badge>
                </div>
                <div className="truncate text-xs text-(--ui-text-tertiary)">{check.message}</div>
              </div>
              <span className="shrink-0 text-[0.625rem] text-(--ui-text-tertiary)">
                {formatRelativeTime(check.lastChecked)}
              </span>
            </div>
          ))}
        </div>
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
