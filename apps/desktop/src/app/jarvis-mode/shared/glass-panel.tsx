import { type HTMLMotionProps, motion } from 'motion/react'
import { memo, type ReactNode } from 'react'

import { cn } from '@/lib/utils'

interface GlassPanelProps extends HTMLMotionProps<'div'> {
  children: ReactNode
  intensity?: 'light' | 'medium' | 'heavy'
  border?: boolean
  glow?: 'cyan' | 'blue' | 'none'
  className?: string
}

const INTENSITY_MAP = {
  light: 'bg-white/[0.02] backdrop-blur-[8px]',
  medium: 'bg-white/[0.04] backdrop-blur-[16px]',
  heavy: 'bg-white/[0.06] backdrop-blur-[24px]',
}

const BORDER_CLASS = 'border border-white/[0.06]'
const BORDER_HOVER = 'hover:border-white/[0.12]'

const GLOW_STYLES: Record<string, string> = {
  cyan: 'shadow-[0_0_20px_rgba(0,212,255,0.08),0_0_60px_rgba(0,212,255,0.03)]',
  blue: 'shadow-[0_0_20px_rgba(0,102,255,0.08),0_0_60px_rgba(0,102,255,0.03)]',
  none: '',
}

function GlassPanelComponent({
  children,
  intensity = 'medium',
  border = true,
  glow = 'none',
  className,
  ...props
}: GlassPanelProps) {
  return (
    <motion.div
      className={cn(
        'rounded-xl',
        INTENSITY_MAP[intensity],
        border && BORDER_CLASS,
        border && BORDER_HOVER,
        GLOW_STYLES[glow],
        'transition-all duration-300',
        className,
      )}
      {...props}
    >
      {children}
    </motion.div>
  )
}

export const GlassPanel = memo(GlassPanelComponent)

export function GlassDivider({ className }: { className?: string }) {
  return (
    <div className={cn('h-px bg-gradient-to-r from-transparent via-white/[0.08] to-transparent', className)} />
  )
}
