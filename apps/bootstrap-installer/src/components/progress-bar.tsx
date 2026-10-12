import clsx from 'clsx'

interface ProgressBarProps {
  value: number
  max: number
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
  className?: string
}

export function ProgressBar({
  value,
  max,
  size = 'md',
  showLabel = false,
  className,
}: ProgressBarProps) {
  const fraction = max > 0 ? Math.min(value / max, 1) : 0
  const percent = Math.round(fraction * 100)

  const heights = { sm: 'h-1', md: 'h-1.5', lg: 'h-2' }

  return (
    <div className={clsx('w-full', className)}>
      <div
        className={clsx(
          'w-full overflow-hidden rounded-full bg-muted',
          heights[size]
        )}
      >
        <div
          className={clsx(
            'h-full rounded-full bg-primary transition-all duration-500 ease-out'
          )}
          style={{ width: `${Math.max(1, percent)}%` }}
        />
      </div>
      {showLabel && (
        <div className="mt-1 text-right text-xs text-muted-foreground">
          {value} / {max}
        </div>
      )}
    </div>
  )
}

interface SegmentedProgressProps {
  segments: Array<{ label: string; active: boolean; completed: boolean }>
  className?: string
}

export function SegmentedProgress({
  segments,
  className,
}: SegmentedProgressProps) {
  const activeIndex = segments.findIndex((s) => s.active)

  return (
    <div className={clsx('flex items-center gap-1', className)}>
      {segments.map((seg, i) => (
        <div key={i} className="flex flex-1 items-center gap-1">
          <div
            className={clsx(
              'flex h-1 flex-1 rounded-full transition-colors duration-300',
              seg.completed && 'bg-primary',
              seg.active && 'bg-primary/60',
              !seg.completed && !seg.active && 'bg-muted'
            )}
          />
          {i < segments.length - 1 && (
            <div
              className={clsx(
                'size-1 rounded-full transition-colors',
                i < activeIndex ? 'bg-primary' : 'bg-muted'
              )}
            />
          )}
        </div>
      ))}
    </div>
  )
}

interface StepIndicatorProps {
  steps: Array<{ label: string }>
  current: number
  className?: string
}

export function StepIndicator({
  steps,
  current,
  className,
}: StepIndicatorProps) {
  return (
    <div className={clsx('flex items-center', className)}>
      {steps.map((step, i) => {
        const state =
          i < current ? 'done' : i === current ? 'active' : 'upcoming'
        return (
          <div key={i} className="flex items-center">
            <div
              className={clsx(
                'flex size-8 shrink-0 items-center justify-center rounded-full text-xs font-medium transition-all',
                state === 'done' && 'bg-primary text-primary-foreground',
                state === 'active' &&
                  'border-2 border-primary bg-background text-primary',
                state === 'upcoming' &&
                  'border border-muted-foreground/30 bg-background text-muted-foreground/60'
              )}
            >
              {state === 'done' ? (
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              ) : (
                i + 1
              )}
            </div>
            <span
              className={clsx(
                'ml-2 text-xs transition-colors',
                state === 'active' && 'font-medium text-foreground',
                state === 'done' && 'text-foreground/70',
                state === 'upcoming' && 'text-muted-foreground/50'
              )}
            >
              {step.label}
            </span>
            {i < steps.length - 1 && (
              <div
                className={clsx(
                  'mx-3 h-px w-8 transition-colors',
                  i < current ? 'bg-primary/40' : 'bg-muted'
                )}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}
