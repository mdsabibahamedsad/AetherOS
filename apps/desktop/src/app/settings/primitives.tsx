import type { ReactNode } from 'react'

import { PageLoader } from '@/components/page-loader'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type { IconComponent } from '@/lib/icons'
import { cn } from '@/lib/utils'

import { PAGE_INSET_X } from '../layout-constants'

// AetherOS Premium Settings Components

export function SettingSection({ title, description, children }: { title: string; description?: string; children: ReactNode }) {
  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-sm font-semibold tracking-tight text-foreground">{title}</h3>
        {description && <p className="mt-1 text-xs text-muted-foreground">{description}</p>}
      </div>
      {children}
    </div>
  )
}

export function SettingsContent({ children }: { children: ReactNode }) {
  return (
    <section className="min-h-0 overflow-hidden">
      <div className={cn('h-full min-h-0 overflow-y-auto pb-20', PAGE_INSET_X)}>
        <div className="mx-auto w-full max-w-4xl">{children}</div>
      </div>
    </section>
  )
}

export function Pill({ tone = 'muted', children }: { tone?: 'muted' | 'primary'; children: ReactNode }) {
  return <Badge variant={tone === 'primary' ? 'default' : 'muted'}>{children}</Badge>
}

export function SectionHeading({ icon: Icon, title, meta }: { icon: IconComponent; title: string; meta?: string }) {
  return (
    <div className="mb-2.5 flex items-center gap-2 pt-2 text-[length:var(--conversation-text-font-size)] font-semibold">
      <Icon className="size-4 text-[#00D4FF]" />
      <span className="bg-gradient-to-r from-[#0066FF] to-[#00D4FF] bg-clip-text text-transparent">{title}</span>
      {meta && <Pill>{meta}</Pill>}
    </div>
  )
}

export function NavLink({
  icon: Icon,
  label,
  active,
  onClick
}: {
  icon: IconComponent
  label: string
  active: boolean
  onClick: () => void
}) {
  return (
    <Button
      className={cn(
        'flex min-h-7 w-full justify-start gap-2 rounded-[8px] px-2 text-left text-[length:var(--conversation-text-font-size)] transition-all duration-200',
        active
          ? 'bg-gradient-to-r from-[rgba(0,102,255,0.12)] to-[rgba(0,212,255,0.06)] text-foreground shadow-[inset_3px_0_0_0_#00D4FF]'
          : 'text-muted-foreground hover:bg-white/5 hover:text-foreground hover:shadow-[inset_3px_0_0_0_rgba(0,212,255,0.2)]'
      )}
      onClick={onClick}
      size="sm"
      type="button"
      variant="ghost"
    >
      <Icon className="size-4 shrink-0" />
      <span className="min-w-0 flex-1 truncate">{label}</span>
    </Button>
  )
}

export function ListRow({
  title,
  description,
  hint,
  action,
  below,
  wide = false
}: {
  title: ReactNode
  description?: ReactNode
  hint?: ReactNode
  action?: ReactNode
  below?: ReactNode
  wide?: boolean
}) {
  return (
    <div
      className={cn(
        'grid gap-3 py-3 sm:grid-cols-[minmax(0,1fr)_minmax(15rem,22rem)] sm:items-center',
        wide && 'sm:grid-cols-1 sm:items-start'
      )}
    >
      <div className="min-w-0">
        <div className="text-[length:var(--conversation-text-font-size)] font-medium text-foreground">{title}</div>
        {description && (
          <div className="mt-1 text-[length:var(--conversation-caption-font-size)] leading-(--conversation-caption-line-height) text-muted-foreground">
            {description}
          </div>
        )}
        {hint && <div className="mt-1 block font-mono text-[0.68rem] text-muted-foreground/60">{hint}</div>}
        {below}
      </div>
      {action && <div className={cn('min-w-0', !wide && 'sm:justify-self-end')}>{action}</div>}
    </div>
  )
}

export function LoadingState({ label }: { label: string }) {
  return <PageLoader label={label} />
}

export function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="grid min-h-48 place-items-center text-center">
      <div className="rounded-[16px] border border-white/5 bg-white/[0.02] p-8 backdrop-blur-sm">
        <div className="text-sm font-semibold text-foreground">{title}</div>
        <div className="mt-2 text-xs text-muted-foreground">{description}</div>
      </div>
    </div>
  )
}
