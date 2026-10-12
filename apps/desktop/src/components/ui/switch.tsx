import { cva, type VariantProps } from 'class-variance-authority'
import { Switch as SwitchPrimitive } from 'radix-ui'
import * as React from 'react'

import { cn } from '@/lib/utils'

// AetherOS Premium Switch
const switchVariants = cva(
  'peer inline-flex shrink-0 items-center rounded-full border border-[color-mix(in_srgb,var(--dt-foreground)_18%,transparent)] bg-[color-mix(in_srgb,var(--dt-background)_58%,var(--dt-input))] shadow-[inset_0_0_0_0.0625rem_color-mix(in_srgb,var(--dt-foreground)_8%,transparent)] transition-all duration-200 outline-none focus-visible:border-ring focus-visible:ring-[0.1875rem] focus-visible:ring-[#00D4FF]/50 disabled:cursor-not-allowed disabled:opacity-50 data-[state=checked]:border-transparent data-[state=checked]:bg-gradient-to-r data-[state=checked]:from-[#0066FF] data-[state=checked]:to-[#00D4FF] data-[state=checked]:shadow-[0_0_12px_rgba(0,212,255,0.3)] hover:border-[#00D4FF]/30',
  {
    variants: {
      size: {
        default: 'h-5 w-9',
        xs: 'h-4 w-7'
      }
    },
    defaultVariants: {
      size: 'default'
    }
  }
)

const switchThumbVariants = cva(
  'pointer-events-none block rounded-full bg-foreground shadow-[0_0.0625rem_0.1875rem_color-mix(in_srgb,var(--dt-background)_50%,transparent)] ring-0 transition-all duration-200 data-[state=unchecked]:translate-x-0 data-[state=checked]:translate-x-4 data-[state=checked]:bg-white data-[state=checked]:shadow-[0_2px_8px_rgba(0,0,0,0.3)]',
  {
    variants: {
      size: {
        default: 'size-4 data-[state=checked]:translate-x-4',
        xs: 'size-3 data-[state=checked]:translate-x-3.5'
      }
    },
    defaultVariants: {
      size: 'default'
    }
  }
)

function Switch({
  className,
  size,
  ...props
}: React.ComponentProps<typeof SwitchPrimitive.Root> & VariantProps<typeof switchVariants>) {
  return (
    <SwitchPrimitive.Root className={cn(switchVariants({ size }), className)} data-slot="switch" {...props}>
      <SwitchPrimitive.Thumb className={switchThumbVariants({ size })} data-slot="switch-thumb" />
    </SwitchPrimitive.Root>
  )
}

export { Switch }
