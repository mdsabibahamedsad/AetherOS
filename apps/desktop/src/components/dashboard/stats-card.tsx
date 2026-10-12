import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

interface StatsCardProps {
  icon: string
  label: string
  value: React.ReactNode
  detail?: string
  trend?: { direction: 'up' | 'down'; value: string }
  valueClass?: string
  loading?: boolean
}

export function StatsCard({ icon, label, value, detail, trend, valueClass, loading }: StatsCardProps) {
  return (
    <div className="group rounded-xl border border-(--ui-stroke-tertiary) bg-(--ui-bg-tertiary)/20 p-4 transition-all hover:border-(--dt-ring) hover:shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-(--ui-text-tertiary)">
          <span className="codicon codicon-{icon} text-base" />
          <span className="text-[0.625rem] font-medium uppercase tracking-widest">{label}</span>
        </div>
        {trend && (
          <span className={cn(
            'flex items-center gap-0.5 text-[0.625rem] font-medium',
            trend.direction === 'up' ? 'text-emerald-500' : 'text-red-500'
          )}>
            <span className={cn(
              'codicon text-[0.5rem]',
              trend.direction === 'up' ? 'codicon-arrow-up' : 'codicon-arrow-down'
            )} />
            {trend.value}
          </span>
        )}
      </div>
      <div className={cn('mt-1.5 text-lg font-semibold tracking-tight', valueClass)}>
        {loading ? <Skeleton className="h-5 w-16" /> : value}
      </div>
      {detail && (
        <div className="mt-0.5 text-[0.6875rem] text-(--ui-text-tertiary)">{detail}</div>
      )}
    </div>
  )
}
