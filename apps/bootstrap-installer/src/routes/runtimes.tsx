import { useEffect, useState } from 'react'
import { useEffect, useState } from 'react'
import { useStore } from '@nanostores/react'
import { invoke } from '@tauri-apps/api/core'
import { Button } from '../components/button'
import { RuntimeCard } from '../components/runtime-card'
import { StepIndicator } from '../components/progress-bar'
import { $route, $runtimeChecks } from '../store'
import { ArrowRight, Loader2 } from 'lucide-react'

const INSTALL_STEPS = [
  { label: 'Welcome' },
  { label: 'Requirements' },
  { label: 'Location' },
  { label: 'Components' },
  { label: 'Runtimes' },
  { label: 'Install' },
]

export default function Runtimes() {
  const checks = useStore($runtimeChecks)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function init() {
      try {
        const result = await invoke<unknown[]>('detect_runtimes')
        $runtimeChecks.set(result as never[])
      } catch (err) {
        console.error('failed to detect runtimes', err)
      }
      setLoading(false)
    }

    void init()
  }, [])

  const allCompatible = checks.length > 0 && checks.every((r) => r.status === 'compatible')

  return (
    <div className="aetheros-fade-in flex h-full flex-col px-12 py-8">
      <StepIndicator steps={INSTALL_STEPS} current={4} className="mb-8" />

      <div className="flex-1">
        <div className="mb-6">
          <h1 className="text-lg font-semibold text-foreground">
            Runtime Dependencies
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            AetherOS bundles its core runtimes (Python, Node.js). Some system dependencies may need manual install.
          </p>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 size={24} className="animate-spin text-primary" />
          </div>
        ) : (
          <div className="space-y-3">
            {checks.map((runtime) => (
              <RuntimeCard key={runtime.kind} runtime={runtime} />
            ))}
          </div>
        )}
      </div>

      <div className="mt-6 flex items-center justify-between border-t border-border pt-4">
        <Button variant="ghost" onClick={() => $route.set('components')}>
          Back
        </Button>
        <div className="flex gap-3">
          <Button onClick={() => $route.set('progress')}>
            Continue
            <ArrowRight size={16} />
          </Button>
        </div>
      </div>
    </div>
  )
}
