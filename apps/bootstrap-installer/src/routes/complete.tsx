import { useState } from 'react'
import { type CSSProperties } from 'react'
import { useStore } from '@nanostores/react'
import { Button } from '../components/button'
import {
  launchAetherosDesktop,
  $aetherosHome,
  $route,
  $bootstrap,
} from '../store'
import { Rocket, Home, RefreshCw, AlertCircle, Cable } from 'lucide-react'

export default function Complete() {
  const aetherosHome = useStore($aetherosHome)
  const bootstrap = useStore($bootstrap)
  const [error, setError] = useState<string | null>(null)
  const [launching, setLaunching] = useState(false)

  async function handleLaunch() {
    setError(null)
    setLaunching(true)
    try {
      await launchAetherosDesktop()
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      setError(msg)
      setLaunching(false)
    }
  }

  const installRoot = bootstrap.installRoot ?? aetherosHome

  return (
    <div className="aetheros-fade-in flex h-full flex-col items-center justify-center gap-8 px-12 py-10">
      <div className="w-full max-w-2xl min-w-0 text-center">
        <div className="mx-auto mb-6 flex size-16 items-center justify-center rounded-2xl bg-emerald-500/10">
          <div className="flex size-10 items-center justify-center rounded-xl bg-emerald-500/20">
            <CheckIcon />
          </div>
        </div>

        <p
          className="fit-text mx-auto mb-4 w-full font-['Collapse'] font-bold uppercase leading-[0.9] tracking-[0.08em] text-midground mix-blend-plus-lighter dark:text-foreground/90"
          style={
            {
              '--fit-text-line-height': '0.9',
              '--fit-text-max': '5rem',
              '--fit-text-min': '2.25rem',
            } as CSSProperties
          }
        >
          <span>
            <span>Install Complete</span>
          </span>
          <span aria-hidden="true">Install Complete</span>
        </p>

        <p className="m-0 text-center text-base leading-normal tracking-tight text-muted-foreground">
          Aetheros has been installed successfully. You can launch it now, or
          any time from your terminal with{' '}
          <code className="rounded bg-muted/60 px-1 py-0.5 font-mono text-sm">
            aetheros desktop
          </code>
          .
        </p>
      </div>

      {installRoot && (
        <div className="flex items-center gap-2 rounded-lg border border-border/60 bg-card/50 px-4 py-2.5 text-xs text-muted-foreground">
          <Home size={14} className="shrink-0" />
          <span>
            Installed to{' '}
            <code className="font-mono text-foreground/60">
              {installRoot}
            </code>
          </span>
        </div>
      )}

      <div className="flex items-center gap-3">
        <Button
          onClick={() => void handleLaunch()}
          size="lg"
          disabled={launching}
          className="inline-flex items-center gap-2 px-6"
        >
          <Rocket size={18} />
          {launching ? 'Launching\u2026' : 'Launch Aetheros'}
        </Button>
        <Button
          variant="outline"
          size="lg"
          onClick={() => $route.set('connectors')}
          className="inline-flex items-center gap-2"
        >
          <Cable size={16} />
          Manage Connectors
        </Button>
        <Button
          variant="outline"
          size="lg"
          onClick={() => $route.set('welcome')}
          className="inline-flex items-center gap-2"
        >
          <RefreshCw size={16} />
          Back to start
        </Button>
      </div>

      {error && (
        <div
          role="alert"
          className="flex max-w-2xl items-start gap-2 rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive"
        >
          <AlertCircle size={16} className="mt-0.5 shrink-0" />
          <div className="min-w-0">
            <div className="font-medium">
              Couldn&rsquo;t launch the desktop app
            </div>
            <div className="mt-1 text-destructive/80">{error}</div>
          </div>
        </div>
      )}
    </div>
  )
}

function CheckIcon() {
  return (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="text-emerald-500"
    >
      <polyline points="20 6 9 17 4 12" />
    </svg>
  )
}
