import { BrandMark } from '@/components/brand-mark'
import { BRAND } from '@/lib/brand'
import { cn } from '@/lib/utils'

interface BrandLogoProps {
  showTagline?: boolean
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

const sizes = {
  sm: { mark: 'size-8', heading: 'text-base', tagline: 'text-[9px]', gap: 'gap-2' },
  md: { mark: 'size-10', heading: 'text-xl', tagline: 'text-[10px]', gap: 'gap-2.5' },
  lg: { mark: 'size-14', heading: 'text-3xl', tagline: 'text-xs', gap: 'gap-3' },
}

export function BrandLogo({ showTagline = false, size = 'md', className }: BrandLogoProps) {
  const s = sizes[size]

  return (
    <div className={cn('inline-flex items-center', s.gap, className)}>
      <BrandMark className={s.mark} />
      <div className="flex flex-col">
        <span className={cn(s.heading, 'font-bold tracking-[-0.03em]', BRAND.textGradient)}>
          AetherOS
        </span>
        {showTagline && (
          <span
            className={cn(
              s.tagline,
              'uppercase tracking-[0.2em] text-muted-foreground/60'
            )}
          >
            AI Operating System
          </span>
        )}
      </div>
    </div>
  )
}
