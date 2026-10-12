import { cva, type VariantProps } from 'class-variance-authority'
import { Slot } from 'radix-ui'
import * as React from 'react'

import { cn } from '@/lib/utils'

// AetherOS Premium Button System
// Text buttons are square (no radius) and sized by padding + line-height — no
// fixed heights — so they stay snug and scale with content. Only icon buttons
// (inherently square) carry the shared 4px radius.
const buttonVariants = cva(
  "inline-flex shrink-0 cursor-pointer items-center justify-center gap-1.5 rounded-[2.5px] text-xs leading-4 font-medium whitespace-nowrap shadow-none transition-all duration-200 outline-none focus-visible:border-ring focus-visible:ring-[0.1875rem] focus-visible:ring-ring/50 disabled:pointer-events-none disabled:cursor-default disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-3.5",
  {
    variants: {
      variant: {
        // AetherOS Primary - Blue gradient with hover lift
        default: 'bg-primary text-primary-foreground hover:bg-primary/90 hover:shadow-[0_4px_12px_rgba(0,102,255,0.3)] hover:-translate-y-0.5 active:translate-y-0',
        // AetherOS Danger - Red with glow
        destructive:
          'bg-destructive text-white hover:bg-destructive/90 hover:shadow-[0_4px_12px_rgba(255,77,106,0.3)] focus-visible:ring-destructive/20 dark:bg-destructive/60 dark:focus-visible:ring-destructive/40',
        // AetherOS Secondary - Glass border with subtle hover
        outline:
          'bg-transparent text-(--ui-text-primary) shadow-[inset_0_0_0_1px_color-mix(in_srgb,var(--ui-stroke-secondary)_50%,transparent)] hover:bg-(--chrome-action-hover) hover:text-(--ui-text-primary) hover:shadow-[inset_0_0_0_1px_color-mix(in_srgb,var(--brand-cyan)_30%,transparent)]',
        // AetherOS Ghost - Glassmorphism fill
        secondary:
          'bg-(--ui-bg-quaternary) text-(--ui-text-primary) hover:bg-(--chrome-action-hover) hover:text-(--ui-text-primary) backdrop-blur-sm',
        // AetherOS Ghost - Minimal with hover glow
        ghost: 'text-(--ui-text-secondary) hover:bg-(--chrome-action-hover) hover:text-(--ui-text-primary) hover:shadow-[inset_0_0_0_1px_rgba(0,212,255,0.1)]',
        link: 'text-primary underline-offset-4 decoration-current/20 hover:underline',
        // Boxless inline-text action (no bg/border). Quiet by default — reads as
        // muted label text, underlines on hover (e.g. "Cancel", "Clear").
        text: 'text-muted-foreground underline-offset-4 hover:text-foreground hover:underline',
        // Emphasized inline-text action: bold + always-underlined link. Use for
        // the actionable affordance in a row ("Change", "Set", "Open logs", …).
        textStrong: 'font-semibold text-muted-foreground underline underline-offset-4 hover:text-foreground',
        // AetherOS Success - Green with glow
        success: 'bg-emerald-600 text-white hover:bg-emerald-500 hover:shadow-[0_4px_12px_rgba(16,185,129,0.3)]',
        // AetherOS Gradient - Brand gradient with animation
        gradient: 'bg-gradient-to-r from-[#0066FF] via-[#00D4FF] to-[#9933FF] text-white hover:shadow-[0_4px_20px_rgba(0,212,255,0.4)] hover:-translate-y-0.5 active:translate-y-0 bg-[length:200%_200%] hover:animate-gradient',
        // AetherOS Glass - Glassmorphism button
        glass: 'bg-white/5 backdrop-blur-md border border-white/10 text-white hover:bg-white/10 hover:border-white/20 hover:shadow-[0_8px_32px_rgba(0,0,0,0.3)]'
      },
      size: {
        default: 'px-3 py-1.5 has-[>svg]:px-2.5',
        xs: "gap-1 px-2 py-0.5 text-[0.6875rem] leading-4 has-[>svg]:px-1.5 [&_svg:not([class*='size-'])]:size-3",
        sm: 'px-2.5 py-1 has-[>svg]:px-2',
        lg: 'px-5 py-2 text-sm leading-5 has-[>svg]:px-4',
        xl: 'px-6 py-2.5 text-base leading-6 has-[>svg]:px-5',
        // Flush inline text action — no box padding/height. Pair with text/link
        // variants when the button must sit inline in a heading or sentence
        // (replaces ad-hoc `h-auto px-0 py-0` overrides).
        inline: 'h-auto gap-1 p-0 has-[>svg]:px-0',
        icon: 'size-9 rounded-[4px]',
        'icon-xs': "size-6 rounded-[4px] [&_svg:not([class*='size-'])]:size-3",
        'icon-sm': 'size-8 rounded-[4px]',
        'icon-lg': 'size-10 rounded-[4px]',
        'icon-titlebar':
          'h-(--titlebar-control-height) w-(--titlebar-control-size) rounded-[4px] [&_.codicon]:text-[0.875rem]'
      }
    },
    defaultVariants: {
      variant: 'default',
      size: 'default'
    }
  }
)

function Button({
  className,
  variant = 'default',
  size = 'default',
  asChild = false,
  ...props
}: React.ComponentProps<'button'> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot.Root : 'button'

  return (
    <Comp
      className={cn(buttonVariants({ variant, size }), className)}
      data-size={size}
      data-slot="button"
      data-variant={variant}
      {...props}
    />
  )
}

export { Button, buttonVariants }
