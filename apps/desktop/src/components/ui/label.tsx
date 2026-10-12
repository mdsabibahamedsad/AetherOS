import { Slot } from 'radix-ui'
import type * as React from 'react'

import { cn } from '@/lib/utils'

export interface LabelProps extends React.ComponentProps<'label'> {
  asChild?: boolean
}

export function Label({ asChild = false, className, ...props }: LabelProps) {
  const Comp = asChild ? Slot.Root : 'label'

  return <Comp className={cn('text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-50', className)} data-slot="label" {...props} />
}
