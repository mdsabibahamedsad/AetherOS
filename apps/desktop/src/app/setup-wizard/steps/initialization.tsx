import { useEffect, useRef, useState } from 'react'

import { cn } from '@/lib/utils'
import { setInitProgress } from '@/store/setup-wizard'

const INIT_PHASES = [
  { id: 'workspace', label: 'Creating workspace' },
  { id: 'memory', label: 'Initializing memory' },
  { id: 'providers', label: 'Configuring providers' },
  { id: 'models', label: 'Setting up models' },
  { id: 'extensions', label: 'Installing extensions' },
  { id: 'plugins', label: 'Configuring plugins' },
  { id: 'services', label: 'Connecting services' },
  { id: 'config', label: 'Writing configuration' },
  { id: 'cache', label: 'Building cache' },
  { id: 'indexes', label: 'Building indexes' }
]

export function InitializationStep({ onComplete }: { onComplete: () => void }) {
  const [progress, setProgress] = useState(0)
  const [currentPhase, setCurrentPhase] = useState(0)
  const [message, setMessage] = useState('')
  const completedRef = useRef(false)

  useEffect(() => {
    if (completedRef.current) {return}
    completedRef.current = true

    let phase = 0
    const totalPhases = INIT_PHASES.length

    const tick = () => {
      if (phase >= totalPhases) {
        setInitProgress(null)
        onComplete()

        return
      }

      setCurrentPhase(phase)
      setMessage(INIT_PHASES[phase].label)
      setProgress(Math.round((phase / totalPhases) * 100))

      const phaseDuration = 400 + Math.random() * 600
      phase++

      // Simulate phase completion
      setTimeout(tick, phaseDuration)
    }

    tick()
  }, [onComplete])

  return (
    <div className="mx-auto flex max-w-xl flex-col items-center justify-center gap-10 py-16 text-center">
      <div className="flex flex-col items-center gap-4">
        <div className="relative">
          <svg className="h-20 w-20 -rotate-90" viewBox="0 0 36 36">
            <circle className="text-muted/30" cx="18" cy="18" fill="none" r="15.5" stroke="currentColor" strokeWidth="2" />
            <circle
              className="text-primary transition-all duration-500" cx="18" cy="18"
              fill="none" r="15.5" stroke="currentColor"
              strokeDasharray={`${(progress / 100) * 97.4} 97.4`}
              strokeLinecap="round"
              strokeWidth="2"
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-lg font-semibold tabular-nums">{progress}%</span>
          </div>
        </div>
      </div>

      <div className="space-y-3">
        <p className="text-lg font-medium">Setting up AetherOS</p>
        <p className="text-sm text-muted-foreground">{message}</p>
      </div>

      <div className="flex flex-wrap justify-center gap-2">
        {INIT_PHASES.map((phase, idx) => (
          <div
            className={cn(
              'flex items-center gap-1.5 rounded-full px-3 py-1 text-xs transition-all',
              idx < currentPhase ? 'bg-green-500/10 text-green-600' :
              idx === currentPhase ? 'bg-primary/10 text-primary animate-pulse' :
              'bg-muted text-muted-foreground/50'
            )}
            key={phase.id}
          >
            {idx < currentPhase ? (
              <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
                <path d="M5 13l4 4L19 7" />
              </svg>
            ) : idx === currentPhase ? (
              <span className="inline-block h-2 w-2 rounded-full bg-primary animate-pulse" />
            ) : (
              <span className="inline-block h-2 w-2 rounded-full bg-muted-foreground/30" />
            )}
            {phase.label}
          </div>
        ))}
      </div>
    </div>
  )
}
