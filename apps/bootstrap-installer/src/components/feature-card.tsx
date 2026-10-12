import { Check, Monitor, Terminal, Grid3X3, Rocket } from 'lucide-react'
import clsx from 'clsx'
import type { LucideIcon } from 'lucide-react'

const FEATURE_ICONS: Record<string, LucideIcon> = {
  desktop: Monitor,
  cli: Terminal,
  shortcuts: Grid3X3,
  auto_launch: Rocket,
}

interface FeatureCardProps {
  id: string
  name: string
  description: string
  icon?: string
  selected: boolean
  required?: boolean
  onChange: (id: string, selected: boolean) => void
}

export function FeatureCard({
  id,
  name,
  description,
  icon,
  selected,
  required = false,
  onChange,
}: FeatureCardProps) {
  const IconComponent = icon ? FEATURE_ICONS[icon] : undefined

  return (
    <button
      type="button"
      onClick={() => !required && onChange(id, !selected)}
      className={clsx(
        'group relative flex w-full items-start gap-4 rounded-lg border p-4 text-left transition-all',
        selected
          ? 'border-primary/40 bg-primary/5 shadow-sm'
          : 'border-border bg-card hover:border-muted-foreground/30 hover:bg-accent/30',
        required && 'cursor-default opacity-90'
      )}
    >
      {IconComponent && (
        <div
          className={clsx(
            'flex size-10 shrink-0 items-center justify-center rounded-lg transition-colors',
            selected
              ? 'bg-primary/10 text-primary'
              : 'bg-muted text-muted-foreground'
          )}
        >
          <IconComponent size={20} />
        </div>
      )}

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span
            className={clsx(
              'text-sm font-medium',
              selected ? 'text-foreground' : 'text-foreground/80'
            )}
          >
            {name}
          </span>
          {required && (
            <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
              Required
            </span>
          )}
        </div>
        <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">
          {description}
        </p>
      </div>

      <div
        className={clsx(
          'flex size-5 shrink-0 items-center justify-center rounded border transition-all',
          selected
            ? 'border-primary bg-primary text-primary-foreground'
            : 'border-muted-foreground/30 bg-background',
          required && 'opacity-50'
        )}
      >
        {selected && <Check size={12} strokeWidth={3} />}
      </div>
    </button>
  )
}
