import { type CSSProperties } from 'react'
import { Button } from '../components/button'
import { $route } from '../store'
import { ArrowRight, Info } from 'lucide-react'

/*
 * Welcome screen.
 *
 * Mirrors the desktop's chat intro (apps/desktop/src/components/chat/intro.tsx):
 *   - AETHEROS wordmark rendered in Collapse Bold, uppercase, tracked
 *   - mix-blend-plus-lighter so the type "glows" on the canvas
 *   - fit-text utility so the wordmark sizes itself to the column
 *
 * No install-path footer. The default install location is correct for
 * 99% of users; the rest will use the CLI installer with a -AetherosHome
 * flag. Showing %LOCALAPPDATA% to grandma is developer-brain.
 */
export default function Welcome() {
  return (
    <div className="aetheros-fade-in flex h-full flex-col items-center justify-center gap-10 px-12 py-10">
      <button
        type="button"
        onClick={() => $route.set('about')}
        className="absolute right-4 top-4 inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-muted-foreground/60 transition-colors hover:text-muted-foreground"
      >
        <Info size={14} />
        About
      </button>

      {/* Hero — same recipe the desktop's chat/intro.tsx uses */}
      <div className="w-full max-w-2xl min-w-0 text-center">
        <p
          className="fit-text mx-auto mb-4 w-full font-['Collapse'] font-bold uppercase leading-[0.9] tracking-[0.08em] text-midground mix-blend-plus-lighter dark:text-foreground/90"
          style={
            {
              '--fit-text-line-height': '0.9',
              '--fit-text-max': '6rem',
              '--fit-text-min': '2.5rem'
            } as CSSProperties
          }
        >
          <span>
            <span>AETHEROS</span>
          </span>
          <span aria-hidden="true">AETHEROS</span>
        </p>

        <p className="m-0 text-center text-base leading-normal tracking-tight text-muted-foreground">
          The agent that grows with you. We&rsquo;ll check your system, pick a
          location, and set everything up in the background.
        </p>
      </div>

      <Button
        onClick={() => $route.set('system-check')}
        size="lg"
        className="group inline-flex items-center gap-2 px-6"
      >
        Get Started
        <ArrowRight
          size={18}
          className="transition-transform group-hover:translate-x-0.5"
        />
      </Button>
    </div>
  )
}
