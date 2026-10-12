import { type WolfColorway, WolfMark } from '@/components/brand/wolf-mark'
import { BRAND } from '@/lib/brand'
import { cn } from '@/lib/utils'

export type BrandLockupLayout = 'mark-only' | 'horizontal' | 'stacked'

export interface BrandLockupProps {
  className?: string
  colorway?: WolfColorway
  /** Wolf tile size in px. Recognizable 16–1024; minimum 16. */
  size?: number
  layout?: BrandLockupLayout
  /** Secondary tagline. Never competes with the wolf: caption scale, muted. */
  tagline?: boolean
  /** Hero/brand moments only: gradient wordmark. UI default is solid text. */
  gradientWordmark?: boolean
}

const WORDMARK_TRACKING = '-0.03em'

/**
 * Official AetherOS lockups. Every configuration cuts the wolf from the
 * single WolfMark master — no redraws, no competing symbols.
 *
 *  - mark-only: favicon, app icon base, avatars, presence dots
 *  - horizontal: Wolf + AetherOS (chrome, headers, installer)
 *  - stacked: Wolf above AetherOS (boot, splash, about)
 *  - + tagline "AI OPERATING SYSTEM" (secondary, muted, tracked out)
 *  - colorway mono + text color = White/Black/Monochrome configs
 */
export function BrandLockup({
  className,
  colorway = 'brand',
  layout = 'horizontal',
  size = 32,
  tagline = false,
  gradientWordmark = false,
}: BrandLockupProps) {
  const mono = colorway === 'mono'
  const wordmarkSize = Math.max(12, Math.round(size * 0.52))

  const mark = (
    <span
      aria-hidden={false}
      className={cn(
        'inline-flex shrink-0 items-center justify-center overflow-hidden',
        mono ? 'rounded-[22%]' : 'rounded-[12px] bg-gradient-to-br from-[#060816] to-[#0B1020]'
      )}
      style={{ width: size, height: size }}
    >
      <WolfMark className="p-[8%]" colorway={colorway} />
    </span>
  )

  if (layout === 'mark-only') {
    return <span className={cn('inline-flex', className)}>{mark}</span>
  }

  const wordmark = (
    <span className="flex min-w-0 flex-col leading-none">
      <span
        className={cn('font-bold', gradientWordmark && !mono ? BRAND.textGradient : 'text-foreground')}
        style={{ fontSize: wordmarkSize, letterSpacing: WORDMARK_TRACKING }}
      >
        AetherOS
      </span>
      {tagline ? (
        <span
          className="mt-1 font-medium uppercase text-muted-foreground/60"
          style={{ fontSize: Math.max(8, Math.round(wordmarkSize * 0.32)), letterSpacing: '0.2em' }}
        >
          AI Operating System
        </span>
      ) : null}
    </span>
  )

  return (
    <span
      className={cn(
        'inline-flex items-center',
        layout === 'stacked' ? 'flex-col text-center' : 'flex-row',
        className
      )}
      style={{ gap: Math.max(6, Math.round(size * 0.25)) }}
    >
      {mark}
      {wordmark}
    </span>
  )
}
