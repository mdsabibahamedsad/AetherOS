import type { ComponentProps } from 'react'

import { BrandMark } from '@/components/brand-mark'
import { Loader } from '@/components/ui/loader'
import { cn } from '@/lib/utils'

interface PageLoaderProps extends Omit<ComponentProps<'div'>, 'children'> {
  label?: string
}

// AetherOS Premium Page Loader
export function PageLoader({
  'aria-label': ariaLabel,
  className,
  label = 'Loading',
  role = 'status',
  ...props
}: PageLoaderProps) {
  return (
    <div
      {...props}
      aria-label={ariaLabel ?? label}
      className={cn('grid h-full place-items-center', className)}
      role={role}
    >
      <div className="flex flex-col items-center gap-4">
        {/* AetherOS Wolf Logo */}
        <div className="relative">
          <div className="absolute inset-0 rounded-full bg-gradient-to-r from-[#0066FF] via-[#00D4FF] to-[#9933FF] opacity-20 blur-xl animate-pulse" />
          <div className="relative rounded-[16px] border border-white/10 bg-[rgba(11,16,32,0.8)] p-4 backdrop-blur-md">
            <BrandMark className="size-12" />
          </div>
        </div>
        {/* Loading indicator */}
        <div className="flex items-center gap-2">
          <Loader
            aria-hidden="true"
            className="size-4 text-[#00D4FF]"
            pathSteps={220}
            role="presentation"
            strokeScale={0.72}
            type="rose-curve"
          />
          <span className="text-xs text-muted-foreground">{label}</span>
        </div>
      </div>
    </div>
  )
}
