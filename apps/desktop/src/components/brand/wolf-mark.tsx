import { useId } from 'react'

import { BRAND } from '@/lib/brand'
import { cn } from '@/lib/utils'

export type WolfColorway = 'brand' | 'mono'

/**
 * Single master AetherOS Wolf geometry. Every logo configuration
 * (Wolf Only, lockups, favicon, installer, avatar) MUST cut from these
 * paths — never a redrawn variant.
 *
 * Geometry is the pre-existing production silhouette (32×32 grid, angular
 * facets, eye glow, muzzle cutout); this module only centralizes it and
 * adds colorways. Silhouette reads without effects: in `mono` the whole
 * mark is one currentColor shape (cutouts go transparent).
 */
export const WOLF_VIEWBOX = '0 0 32 32'

export const WOLF_FUR_PATH =
  'M16 0 L5 2 L1 6 L4 10 L2 14 L0 20 L3 25 L8 29 L16 32 L24 29 L29 25 L32 20 L30 14 L28 10 L31 6 L27 2 Z'

export const WOLF_CUTOUT_PATHS = [
  'M14 7 L6 24 L8 24 L15 7 Z',
  'M17 7 L24 24 L26 24 L18 7 Z',
  'M11 16 L21 16 L21 18 L11 18 Z',
] as const

export interface WolfMarkProps extends React.ComponentProps<'svg'> {
  colorway?: WolfColorway
  /** Accessible label. Omit (with aria-hidden) only when purely decorative. */
  label?: string
}

export function WolfMark({ className, colorway = 'brand', label = 'AetherOS wolf', ...props }: WolfMarkProps) {
  const uid = useId().replace(/[^a-zA-Z0-9]/g, '')
  const furId = `wolf-fur-${uid}`
  const eyeId = `wolf-eye-${uid}`
  const mono = colorway === 'mono'

  return (
    <svg
      aria-label={label}
      className={cn('size-full object-contain', className)}
      role="img"
      viewBox={WOLF_VIEWBOX}
      {...props}
    >
      {!mono ? (
        <defs>
          <linearGradient id={furId} x1="0%" x2="100%" y1="0%" y2="100%">
            <stop offset="0%" stopColor={BRAND.colors.blue} />
            <stop offset="50%" stopColor={BRAND.colors.cyan} />
            <stop offset="100%" stopColor={BRAND.colors.purple} />
          </linearGradient>
          <linearGradient id={eyeId} x1="0%" x2="100%" y1="0%" y2="100%">
            <stop offset="0%" stopColor={BRAND.colors.eyeGlowFrom} />
            <stop offset="100%" stopColor={BRAND.colors.eyeGlowTo} />
          </linearGradient>
        </defs>
      ) : null}

      <path d={WOLF_FUR_PATH} fill={mono ? 'currentColor' : `url(#${furId})`} />

      {WOLF_CUTOUT_PATHS.map(d => (
        <path d={d} fill={mono ? 'none' : BRAND.colors.dark} key={d} />
      ))}

      <ellipse
        cx="8"
        cy="12"
        fill={mono ? 'currentColor' : `url(#${eyeId})`}
        rx="1.3"
        ry="0.7"
      />
      <ellipse
        cx="24"
        cy="12"
        fill={mono ? 'currentColor' : `url(#${eyeId})`}
        rx="1.3"
        ry="0.7"
      />

      <ellipse cx="16" cy="27" fill={mono ? 'none' : BRAND.colors.dark} rx="1.8" ry="1" />
    </svg>
  )
}
