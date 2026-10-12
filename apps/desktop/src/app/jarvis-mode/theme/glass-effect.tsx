import { motion } from 'motion/react'
import { type CSSProperties, memo, type ReactNode, useRef } from 'react'

import { cn } from '@/lib/utils'

interface GlassEffectProps {
  children: ReactNode
  className?: string
  style?: CSSProperties
  border?: boolean
  glowColor?: string
  blur?: 'sm' | 'md' | 'lg'
  hover?: boolean
}

export const GlassCard = memo(function GlassCard({
  children,
  className,
  style,
  border = true,
  glowColor,
  blur = 'md',
  hover = true,
}: GlassEffectProps) {
  const ref = useRef<HTMLDivElement>(null)

  const BLUR_MAP = { sm: '8px', md: '16px', lg: '24px' }

  return (
    <motion.div
      className={cn(
        'relative overflow-hidden rounded-xl',
        'bg-white/[0.03]',
        `backdrop-blur-[${BLUR_MAP[blur]}]`,
        border && 'border border-white/[0.06]',
        hover && 'hover:border-white/[0.12]',
        'transition-all duration-300',
        className,
      )}
      ref={ref}
      style={{
        ...style,
        ...(glowColor ? {
          boxShadow: `0 0 30px ${glowColor}08, inset 0 0 30px ${glowColor}04`,
        } : {}),
      }}
      whileHover={hover ? { scale: 1.01 } : undefined}
    >
      {children}
    </motion.div>
  )
})

export const GlassButton = memo(function GlassButton({
  children,
  className,
  active,
  ...props
}: {
  children: ReactNode
  className?: string
  active?: boolean
} & React.ComponentProps<'button'>) {
  return (
    <button
      className={cn(
        'px-3 py-1.5 rounded-lg text-[11px] font-medium transition-all duration-200',
        'border border-white/[0.06]',
        active
          ? 'bg-[#00d4ff]/10 border-[#00d4ff]/30 text-[#00d4ff]'
          : 'bg-white/[0.03] text-white/40 hover:bg-white/[0.06] hover:text-white/60 hover:border-white/[0.12]',
        className,
      )}
      {...props}
    >
      {children}
    </button>
  )
})

export function GlowBorder({ color = '#00d4ff', className }: { color?: string; className?: string }) {
  return (
    <div
      className={cn('absolute inset-0 rounded-xl pointer-events-none', className)}
      style={{
        background: `linear-gradient(135deg, ${color}20, transparent 50%, ${color}10)`,
        opacity: 0.5,
      }}
    />
  )
}
