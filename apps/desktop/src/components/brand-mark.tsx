import { WolfMark } from '@/components/brand/wolf-mark'
import { BRAND } from '@/lib/brand'
import { cn } from '@/lib/utils'

// Canonical in-app wolf badge. Geometry lives in WolfMark (single master);
// this wrapper preserves the established dark-tile presentation byte for
// byte so all existing usages are unaffected.
export function BrandMark({ className, ...props }: React.ComponentProps<'span'>) {
  return (
    <span
      className={cn(
        'inline-flex size-14 shrink-0 items-center justify-center overflow-hidden rounded-[12px] bg-gradient-to-br from-[#060816] to-[#0B1020]',
        className
      )}
      {...props}
    >
      <WolfMark className="p-1" label="AetherOS wolf" />
    </span>
  )
}

export { BRAND }
