import { Check, AlertTriangle, XCircle, Loader2 } from 'lucide-react'
import clsx from 'clsx'

export interface CheckItemData {
  name: string
  label: string
  passed: boolean
  warning: boolean
  message: string
}

interface SystemCheckCardProps {
  check: CheckItemData
  running?: boolean
}

export function SystemCheckCard({ check, running }: SystemCheckCardProps) {
  return (
    <div
      className={clsx(
        'flex items-start gap-3 rounded-lg border px-4 py-3 transition-all',
        check.passed && !check.warning && 'border-emerald-500/20 bg-emerald-500/5',
        check.warning && 'border-amber-500/20 bg-amber-500/5',
        !check.passed && 'border-red-500/20 bg-red-500/10',
        running && 'border-primary/20 bg-primary/5'
      )}
    >
      <div className="mt-0.5 shrink-0">
        {running ? (
          <Loader2 size={18} className="animate-spin text-primary" />
        ) : check.passed && !check.warning ? (
          <div className="flex size-[18px] items-center justify-center rounded-full bg-emerald-500/20">
            <Check size={12} className="text-emerald-500" />
          </div>
        ) : check.warning ? (
          <AlertTriangle size={18} className="text-amber-500" />
        ) : (
          <XCircle size={18} className="text-red-500" />
        )}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span
            className={clsx(
              'text-sm font-medium',
              running && 'text-foreground',
              check.passed && !running && 'text-foreground/80',
              check.warning && !running && 'text-amber-600 dark:text-amber-400',
              !check.passed && !running && 'text-red-600 dark:text-red-400'
            )}
          >
            {check.label}
          </span>
          {!running && (
            <span
              className={clsx(
                'shrink-0 text-xs',
                check.passed && !check.warning && 'text-emerald-600 dark:text-emerald-400',
                check.warning && 'text-amber-600 dark:text-amber-400',
                !check.passed && 'text-red-600 dark:text-red-400'
              )}
            >
              {check.passed && !check.warning
                ? 'Passed'
                : check.warning
                  ? 'Warning'
                  : 'Failed'}
            </span>
          )}
        </div>
        <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">
          {check.message}
        </p>
      </div>
    </div>
  )
}
