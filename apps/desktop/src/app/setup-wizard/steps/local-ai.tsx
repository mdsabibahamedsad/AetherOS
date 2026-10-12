import { useEffect, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Loader } from '@/components/ui/loader'
import { cn } from '@/lib/utils'

interface LocalEnv {
  hasOllama: boolean
  hasLmStudio: boolean
  cuda: boolean
  rocm: boolean
  appleMetal: boolean
  totalRam: string
  gpuMemory: string
  installedModels: string[]
}

export function LocalAiStep() {
  const [detecting, setDetecting] = useState(true)
  const [env, setEnv] = useState<LocalEnv | null>(null)

  useEffect(() => {
    const detect = async () => {
      await new Promise(r => setTimeout(r, 1500))
      const hasOllama = false
      const hasLmStudio = false
      setEnv({
        hasOllama,
        hasLmStudio,
        cuda: false,
        rocm: false,
        appleMetal: false,
        totalRam: '--',
        gpuMemory: '--',
        installedModels: []
      })
      setDetecting(false)
    }

    void detect()
  }, [])

  if (detecting) {
    return (
      <div className="mx-auto flex max-w-xl flex-col items-center justify-center gap-4 py-20">
        <Loader className="h-10 w-10" />
        <p className="text-muted-foreground">Detecting local AI environment...</p>
        <div className="flex gap-2">
          {['ollama', 'cuda', 'metal'].map(label => (
            <span className="h-2 w-16 animate-pulse rounded-full bg-muted" key={label} />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-xl space-y-8 py-8">
      <div>
        <h2 className="text-2xl font-semibold">Local AI</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Detected local AI capabilities
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {[
          { label: 'Ollama', active: env?.hasOllama },
          { label: 'LM Studio', active: env?.hasLmStudio },
          { label: 'CUDA', active: env?.cuda },
          { label: 'ROCm', active: env?.rocm },
          { label: 'Apple Metal', active: env?.appleMetal }
        ].map(item => (
          <div className={cn(
            'flex items-center justify-between rounded-xl border p-4',
            item.active ? 'border-green-500/20 bg-green-500/5' : 'border-border opacity-50'
          )} key={item.label}>
            <span className="text-sm font-medium">{item.label}</span>
            <div className={cn('h-2.5 w-2.5 rounded-full', item.active ? 'bg-green-500' : 'bg-muted-foreground/30')} />
          </div>
        ))}
      </div>

      <div className="rounded-xl border p-4">
        <h3 className="mb-3 text-sm font-medium text-muted-foreground">System Resources</h3>
        <div className="grid grid-cols-2 gap-4">
          {[
            { label: 'Total RAM', value: env?.totalRam ?? '--' },
            { label: 'GPU Memory', value: env?.gpuMemory ?? '--' }
          ].map(item => (
            <div key={item.label}>
              <div className="text-xs text-muted-foreground">{item.label}</div>
              <div className="font-mono text-sm font-medium">{item.value}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-xl border p-4">
        <h3 className="mb-3 text-sm font-medium text-muted-foreground">Installed Models</h3>
        {env?.installedModels && env.installedModels.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {env.installedModels.map(m => <Badge key={m} variant="secondary">{m}</Badge>)}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No local models detected</p>
        )}
      </div>
    </div>
  )
}
