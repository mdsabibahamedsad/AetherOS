import { type ElementType, memo, type ReactNode } from 'react'

import { cn } from '@/lib/utils'

interface NeonTextProps {
  children: ReactNode
  color?: 'cyan' | 'blue' | 'purple' | 'emerald' | 'amber' | 'red' | 'white'
  size?: 'xs' | 'sm' | 'base' | 'md' | 'lg' | 'xl'
  weight?: 'normal' | 'medium' | 'semibold' | 'bold'
  tracking?: 'tight' | 'normal' | 'wide' | 'wider' | 'widest'
  glow?: boolean
  className?: string
  as?: 'span' | 'div' | 'p' | 'h1' | 'h2' | 'h3'
}

const COLOR_MAP = {
  cyan: 'text-[#00d4ff]',
  blue: 'text-[#0066ff]',
  purple: 'text-[#9933ff]',
  emerald: 'text-[#22c55e]',
  amber: 'text-[#f59e0b]',
  red: 'text-[#ef4444]',
  white: 'text-white/80',
}

const GLOW_MAP: Record<string, string> = {
  cyan: 'text-shadow-[0_0_10px_rgba(0,212,255,0.5),0_0_30px_rgba(0,212,255,0.2)]',
  blue: 'text-shadow-[0_0_10px_rgba(0,102,255,0.5),0_0_30px_rgba(0,102,255,0.2)]',
  purple: 'text-shadow-[0_0_10px_rgba(153,51,255,0.5)]',
  emerald: 'text-shadow-[0_0_10px_rgba(34,197,94,0.5)]',
  amber: 'text-shadow-[0_0_10px_rgba(245,158,11,0.5)]',
  red: 'text-shadow-[0_0_10px_rgba(239,68,68,0.5)]',
  white: '',
}

const SIZE_MAP = {
  xs: 'text-[9px]',
  sm: 'text-[11px]',
  base: 'text-[13px]',
  md: 'text-[15px]',
  lg: 'text-[18px]',
  xl: 'text-[24px]',
}

const WEIGHT_MAP = {
  normal: 'font-normal',
  medium: 'font-medium',
  semibold: 'font-semibold',
  bold: 'font-bold',
}

const TRACKING_MAP = {
  tight: 'tracking-tight',
  normal: 'tracking-normal',
  wide: 'tracking-wide',
  wider: 'tracking-wider',
  widest: 'tracking-widest',
}

const TAG_MAP: Record<string, ElementType> = {
  span: 'span',
  div: 'div',
  p: 'p',
  h1: 'h1',
  h2: 'h2',
  h3: 'h3',
}

function NeonTextComponent({
  children,
  color = 'white',
  size = 'base',
  weight = 'normal',
  tracking = 'normal',
  glow = false,
  className,
  as = 'span',
}: NeonTextProps) {
  const Tag: ElementType = TAG_MAP[as]

  return (
    <Tag
      className={cn(
        COLOR_MAP[color],
        SIZE_MAP[size],
        WEIGHT_MAP[weight],
        TRACKING_MAP[tracking],
        glow && GLOW_MAP[color],
        className,
      )}
    >
      {children}
    </Tag>
  )
}

export const NeonText = memo(NeonTextComponent)
