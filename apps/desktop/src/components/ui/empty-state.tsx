import type { ReactNode } from 'react'

import { Codicon } from '@/components/ui/codicon'
import { cn } from '@/lib/utils'

export interface EmptyStateProps {
  action?: ReactNode
  children?: ReactNode
  className?: string
  description?: ReactNode
  /** Codicon glyph name (e.g. "zap", "shield", "history"). */
  icon?: string
  title: ReactNode
}

// Canonical empty state: muted glyph over a title + guidance copy, with an
// optional action row. Every "no data" view must explain what would be here
// and what the user can do — never a bare "No data."
export function EmptyState({ action, children, className, description, icon, title }: EmptyStateProps) {
  return (
    <div className={cn('grid place-items-center px-4 py-8 text-center', className)}>
      <div>
        {icon && <Codicon className="mx-auto mb-2 text-muted-foreground/40" name={icon} size="2rem" />}
        <div className="text-sm font-medium text-muted-foreground">{title}</div>
        {description && <div className="mx-auto mt-1 max-w-sm text-xs text-muted-foreground/60">{description}</div>}
        {children}
        {action && <div className="mt-3">{action}</div>}
      </div>
    </div>
  )
}
