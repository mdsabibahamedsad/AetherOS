import { useState, useEffect, useCallback } from 'react'
import { invoke } from '@tauri-apps/api/core'
import { Button } from '../components/button'
import { SystemCheckCard, type CheckItemData } from '../components/system-check-card'
import { StepIndicator } from '../components/progress-bar'
import { $route } from '../store'
import { ArrowRight, RefreshCw } from 'lucide-react'

const INSTALL_STEPS = [
  { label: 'Welcome' },
  { label: 'Requirements' },
  { label: 'Location' },
  { label: 'Components' },
  { label: 'Runtimes' },
  { label: 'Install' },
]

export default function SystemCheck() {
  const [checks, setChecks] = useState<CheckItemData[]>([])
  const [running, setRunning] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const allPassed = checks.length > 0 && checks.every((c) => c.passed)

  const runChecks = useCallback(async () => {
    setRunning(true)
    setError(null)
    try {
      const result = await invoke<{
        checks: CheckItemData[]
        all_passed: boolean
        has_warnings: boolean
      }>('run_system_checks')
      setChecks(result.checks)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setRunning(false)
    }
  }, [])

  useEffect(() => {
    void runChecks()
  }, [runChecks])

  return (
    <div className="aetheros-fade-in flex h-full flex-col px-12 py-8">
      <StepIndicator steps={INSTALL_STEPS} current={1} className="mb-8" />

      <div className="flex-1">
        <div className="mb-6">
          <h1 className="text-lg font-semibold text-foreground">
            System Requirements
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Checking if your system meets the requirements to run Aetheros.
          </p>
        </div>

        <div className="space-y-2.5">
          {checks.map((check) => (
            <SystemCheckCard key={check.name} check={check} running={running && !checks.length} />
          ))}
          {running && checks.length === 0 && (
            <>
              {['os', 'arch', 'disk', 'memory'].map((name) => (
                <SystemCheckCard
                  key={name}
                  check={{ name, label: name === 'os' ? 'Operating System' : name === 'arch' ? 'System Architecture' : name === 'disk' ? 'Disk Space' : 'Memory (RAM)', passed: false, warning: false, message: '' }}
                  running
                />
              ))}
            </>
          )}
          {error && (
            <div className="rounded-md border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-600 dark:text-red-400">
              {error}
            </div>
          )}
        </div>

        {!running && checks.length > 0 && !allPassed && (
          <div className="mt-4 rounded-md border border-amber-500/20 bg-amber-500/5 px-4 py-3 text-sm text-amber-600 dark:text-amber-400">
            Some requirements are not met. You can still proceed, but Aetheros
            may not run optimally.
          </div>
        )}
      </div>

      <div className="mt-6 flex items-center justify-between border-t border-border pt-4">
        <Button variant="ghost" onClick={() => $route.set('welcome')}>
          Back
        </Button>
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={() => void runChecks()}
            className="inline-flex items-center gap-1.5"
          >
            <RefreshCw size={14} />
            Re-check
          </Button>
          <Button
            onClick={() => $route.set('location')}
            disabled={running}
            className="inline-flex items-center gap-2"
          >
            Continue
            <ArrowRight size={16} />
          </Button>
        </div>
      </div>
    </div>
  )
}
