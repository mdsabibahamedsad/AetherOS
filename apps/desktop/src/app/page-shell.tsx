import { type ReactNode } from 'react'

import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'

interface PageShellProps {
  children: ReactNode
  className?: string
  header?: ReactNode
}

export function PageShell({ children, className, header }: PageShellProps) {
  return (
    <div className={cn('flex h-full flex-col', className)}>
      {header && (
        <div className="flex h-10 shrink-0 items-center border-b border-(--ui-stroke-tertiary) px-4">
          {header}
        </div>
      )}
      <ScrollArea className="flex-1">
        <div className="p-4">{children}</div>
      </ScrollArea>
    </div>
  )
}

export function PageHeader({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn('flex items-center justify-between', className)}>
      {children}
    </div>
  )
}

export function PageTitle({ children }: { children: ReactNode }) {
  return <h1 className="text-lg font-semibold tracking-tight">{children}</h1>
}

export function PageDescription({ children }: { children: ReactNode }) {
  return <p className="mt-0.5 text-sm text-(--ui-text-tertiary)">{children}</p>
}
