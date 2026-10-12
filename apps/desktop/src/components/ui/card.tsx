import { cva, type VariantProps } from 'class-variance-authority'
import type * as React from 'react'

import { cn } from '@/lib/utils'

const cardVariants = cva(
  'rounded-xl border transition-all',
  {
    variants: {
      variant: {
        default: 'border-(--ui-stroke-tertiary) bg-(--ui-bg-tertiary)/20',
        elevated: 'border-(--ui-stroke-secondary) bg-(--ui-bg-primary) shadow-sm hover:shadow-md',
        glass: 'border-white/10 bg-white/5 backdrop-blur-md',
        ghost: 'border-transparent bg-(--ui-bg-tertiary)/10'
      },
      padding: {
        none: '',
        sm: 'p-3',
        md: 'p-4',
        lg: 'p-6'
      }
    },
    defaultVariants: {
      variant: 'default',
      padding: 'md'
    }
  }
)

export interface CardProps
  extends React.ComponentProps<'div'>,
    VariantProps<typeof cardVariants> {}

export function Card({ className, variant, padding, ...props }: CardProps) {
  return <div className={cn(cardVariants({ variant, padding }), className)} data-slot="card" {...props} />
}

export function CardHeader({ className, ...props }: React.ComponentProps<'div'>) {
  return <div className={cn('mb-3 flex items-center justify-between', className)} {...props} />
}

export function CardTitle({ className, ...props }: React.ComponentProps<'h3'>) {
  return <h3 className={cn('text-sm font-semibold tracking-tight', className)} {...props} />
}

export function CardDescription({ className, ...props }: React.ComponentProps<'p'>) {
  return <p className={cn('text-xs text-(--ui-text-tertiary)', className)} {...props} />
}

export function CardContent({ className, ...props }: React.ComponentProps<'div'>) {
  return <div className={cn(className)} {...props} />
}

export function CardFooter({ className, ...props }: React.ComponentProps<'div'>) {
  return <div className={cn('mt-3 flex items-center gap-2 border-t border-(--ui-stroke-tertiary)/50 pt-3', className)} {...props} />
}

export { cardVariants }
