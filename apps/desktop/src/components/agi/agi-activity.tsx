import { cn } from '@/lib/utils'

export type AgiActivityState = 'done' | 'active' | 'pending' | 'failed'

export interface AgiActivityRow {
  detail?: string | null
  id: string
  label: string
  state: AgiActivityState
}

export interface AgiActivityListProps {
  className?: string
  rows: AgiActivityRow[]
  subtitle?: string | null
  title: string
}

const GLYPH: Record<AgiActivityState, { char: string; tone: string }> = {
  done: { char: '✓', tone: 'text-emerald-500' },
  active: { char: '●', tone: 'text-[#00D4FF]' },
  pending: { char: '○', tone: 'text-muted-foreground/50' },
  failed: { char: '✕', tone: 'text-red-500' },
}

/**
 * Foundational AGI activity language: concise status summaries (done /
 * active / pending / failed) for thinking, working, tool execution, file
 * operations, research, automation, agent activity, approvals, and
 * background tasks. Presentational only — rows are props, never inferred.
 * Private chain-of-thought is never a row: labels must be observable
 * actions or summaries.
 */
export function AgiActivityList({ className, rows, subtitle, title }: AgiActivityListProps) {
  return (
    <section aria-label={title} className={cn('min-w-0', className)} data-testid="agi-activity">
      <p className="text-[0.66rem] font-semibold uppercase tracking-wider text-muted-foreground/70">
        {title}
      </p>
      {subtitle ? <p className="mt-0.5 text-xs text-muted-foreground/80">{subtitle}</p> : null}
      <ul className="mt-2 grid gap-1.5">
        {rows.map(row => {
          const glyph = GLYPH[row.state]

          return (
            <li className="flex min-w-0 items-baseline gap-2 text-[0.78rem] leading-relaxed" key={row.id}>
              <span
                aria-hidden={false}
                aria-label={row.state}
                className={cn('shrink-0 font-medium', glyph.tone)}
                role="img"
              >
                {glyph.char}
              </span>
              <span className="min-w-0 flex-1 truncate text-foreground/90">
                {row.label}
                {row.detail ? <span className="text-muted-foreground/70"> · {row.detail}</span> : null}
              </span>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
