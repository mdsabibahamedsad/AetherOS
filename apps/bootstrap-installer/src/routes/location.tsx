import { useState, useEffect } from 'react'
import { invoke } from '@tauri-apps/api/core'
import { Button } from '../components/button'
import { StepIndicator } from '../components/progress-bar'
import { $route, $installConfig } from '../store'
import { ArrowRight, FolderOpen, AlertCircle, Check } from 'lucide-react'
import clsx from 'clsx'

const INSTALL_STEPS = [
  { label: 'Welcome' },
  { label: 'Requirements' },
  { label: 'Location' },
  { label: 'Components' },
  { label: 'Runtimes' },
  { label: 'Install' },
]

interface LocationCheckResult {
  valid: boolean
  writable: boolean
  exists: boolean
  free_space: string | null
  message: string
}

export default function Location() {
  const config = $installConfig.get()
  const [location, setLocation] = useState(config.install_location)
  const [checking, setChecking] = useState(false)
  const [result, setResult] = useState<LocationCheckResult | null>(null)

  useEffect(() => {
    const timer = setTimeout(() => {
      if (location.trim()) {
        setChecking(true)
        invoke<LocationCheckResult>('validate_install_location', { location })
          .then(setResult)
          .catch(() => setResult(null))
          .finally(() => setChecking(false))
      }
    }, 300)
    return () => clearTimeout(timer)
  }, [location])

  async function handleContinue() {
    await invoke('set_install_location', { location })
    $route.set('components')
  }

  return (
    <div className="aetheros-fade-in flex h-full flex-col px-12 py-8">
      <StepIndicator steps={INSTALL_STEPS} current={2} className="mb-8" />

      <div className="flex-1">
        <div className="mb-6">
          <h1 className="text-lg font-semibold text-foreground">
            Install Location
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Choose where to install Aetheros.
          </p>
        </div>

        <div className="space-y-4">
          <div>
            <label
              htmlFor="install-location"
              className="mb-1.5 block text-xs font-medium text-foreground/80"
            >
              Installation directory
            </label>
            <div className="relative">
              <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
                <FolderOpen size={16} className="text-muted-foreground" />
              </div>
              <input
                id="install-location"
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                className="w-full rounded-lg border border-input bg-background py-2 pl-10 pr-3 text-sm text-foreground outline-none transition-colors focus:border-ring focus:ring-1 focus:ring-ring/30"
              />
            </div>
          </div>

          {checking && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <div className="size-3.5 animate-spin rounded-full border-2 border-muted-foreground/30 border-t-muted-foreground" />
              Checking location...
            </div>
          )}

          {result && !checking && (
            <div
              className={clsx(
                'flex items-start gap-2 rounded-lg border px-4 py-3 text-sm',
                result.valid
                  ? 'border-emerald-500/20 bg-emerald-500/5 text-emerald-600 dark:text-emerald-400'
                  : 'border-red-500/20 bg-red-500/10 text-red-600 dark:text-red-400'
              )}
            >
              {result.valid ? (
                <Check size={16} className="mt-0.5 shrink-0" />
              ) : (
                <AlertCircle size={16} className="mt-0.5 shrink-0" />
              )}
              <span>{result.message}</span>
            </div>
          )}

          <div className="rounded-lg border border-border bg-card/50 px-4 py-3">
            <p className="text-xs text-muted-foreground/70">
              Aetheros will be installed to{' '}
              <code className="font-mono text-foreground/60">
                {location}
              </code>
              . This location can be changed later.
            </p>
          </div>
        </div>
      </div>

      <div className="mt-6 flex items-center justify-between border-t border-border pt-4">
        <Button variant="ghost" onClick={() => $route.set('system-check')}>
          Back
        </Button>
        <Button
          onClick={() => void handleContinue()}
          disabled={checking || !result?.valid}
          className="inline-flex items-center gap-2"
        >
          Continue
          <ArrowRight size={16} />
        </Button>
      </div>
    </div>
  )
}
