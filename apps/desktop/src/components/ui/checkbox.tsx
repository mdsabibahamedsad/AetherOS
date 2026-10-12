import { Checkbox as CheckboxPrimitive } from 'radix-ui'
import * as React from 'react'

import { Codicon } from '@/components/ui/codicon'
import { cn } from '@/lib/utils'

function Checkbox({ className, ...props }: React.ComponentProps<typeof CheckboxPrimitive.Root>) {
  return (
    <CheckboxPrimitive.Root
      className={cn(
        'peer size-4 shrink-0 rounded-[4px] border border-input shadow-xs outline-none transition-all duration-200 focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-[#00D4FF]/50 disabled:cursor-not-allowed disabled:opacity-50 data-[state=checked]:border-[#0066FF] data-[state=checked]:bg-gradient-to-br data-[state=checked]:from-[#0066FF] data-[state=checked]:to-[#00D4FF] data-[state=checked]:text-white hover:border-[#00D4FF]/50 hover:shadow-[0_0_8px_rgba(0,212,255,0.2)] aria-invalid:border-destructive aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40',
        className
      )}
      data-slot="checkbox"
      {...props}
    >
      <CheckboxPrimitive.Indicator
        className="flex items-center justify-center text-current"
        data-slot="checkbox-indicator"
      >
        <Codicon name="check" size="0.875rem" />
      </CheckboxPrimitive.Indicator>
    </CheckboxPrimitive.Root>
  )
}

export { Checkbox }
