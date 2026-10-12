import { useStore } from '@nanostores/react'
import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'

import { getGlobalModelOptions } from '@/aetheros'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Loader } from '@/components/ui/loader'
import { cn } from '@/lib/utils'
import { $setupWizard, setModels, toggleModelFavorite } from '@/store/setup-wizard'
import type { WizardModel } from '@/store/setup-wizard'

function ModelCard({ model, selected, onToggle, onFavorite }: {
  model: WizardModel
  selected: boolean
  onToggle: () => void
  onFavorite: () => void
}) {
  return (
    <button
      className={cn(
        'group flex items-center gap-3 rounded-lg border px-4 py-3 text-left transition-all w-full',
        selected
          ? 'border-primary/40 bg-primary/5'
          : 'border-border hover:border-muted-foreground/20'
      )}
      onClick={onToggle}
      type="button"
    >
      <div className={cn(
        'flex h-5 w-5 shrink-0 items-center justify-center rounded border transition-colors',
        selected ? 'border-primary bg-primary text-primary-foreground' : 'border-muted-foreground/30'
      )}>
        {selected && <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth={3} viewBox="0 0 24 24"><path d="M5 13l4 4L19 7" /></svg>}
      </div>
      <span className="flex-1 truncate font-mono text-sm">{model.name}</span>
      <div className="flex items-center gap-1.5">
        {model.isFast && <Badge className="h-5 px-1.5 text-[10px]" variant="secondary">Fast</Badge>}
        {model.isReasoning && <Badge className="h-5 px-1.5 text-[10px]" variant="secondary">Reason</Badge>}
        {model.isVision && <Badge className="h-5 px-1.5 text-[10px]" variant="secondary">Vision</Badge>}
        {model.isLongContext && <Badge className="h-5 px-1.5 text-[10px]" variant="secondary">Long</Badge>}
      </div>
      <button
        className={cn(
          'shrink-0 opacity-0 transition-all group-hover:opacity-100',
          model.favorite && '!opacity-100'
        )}
        onClick={e => { e.stopPropagation(); onFavorite() }}
        type="button"
      >
        <svg className={cn('h-4 w-4', model.favorite ? 'text-yellow-500 fill-yellow-500' : 'text-muted-foreground')} fill={model.favorite ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
          <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
        </svg>
      </button>
    </button>
  )
}

export function ModelsStep() {
  const state = useStore($setupWizard)
  const [search, setSearch] = useState('')
  const [filterProvider, setFilterProvider] = useState<string | null>(null)

  const { data: modelOptions, isLoading } = useQuery({
    queryKey: ['model-options'],
    queryFn: getGlobalModelOptions,
    staleTime: 60000
  })

  const allModels = useMemo(() => {
    if (!modelOptions?.providers) {return []}
    const result: WizardModel[] = []
    const seen = new Set<string>()

    for (const p of modelOptions.providers) {
      for (const m of (p.models || [])) {
        if (!seen.has(m)) {
          seen.add(m)
          result.push({
            id: m,
            name: m,
            favorite: false,
            isDefault: false,
            isCoding: false,
            isReasoning: false,
            isFast: false,
            isVision: false,
            isLongContext: false
          })
        }
      }
    }

    return result
  }, [modelOptions])

  const filtered = useMemo(() => {
    let list = allModels

    if (search) {
      const q = search.toLowerCase()
      list = list.filter(m => m.name.toLowerCase().includes(q))
    }

    return list
  }, [allModels, search])

  const toggleModel = (model: WizardModel) => {
    const current = state.models
    const idx = current.findIndex(m => m.id === model.id)

    if (idx >= 0) {
      setModels(current.filter(m => m.id !== model.id))
    } else {
      setModels([...current, { ...model, isDefault: current.length === 0 }])
    }
  }

  if (isLoading) {
    return <div className="flex items-center justify-center py-20"><Loader className="h-8 w-8" /></div>
  }

  return (
    <div className="mx-auto max-w-2xl space-y-8 py-8">
      <div>
        <h2 className="text-2xl font-semibold">Model Selection</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Choose the models you want to use. Select multiple for different tasks.
        </p>
      </div>

      <Input
        className="font-mono text-sm"
        onChange={e => setSearch(e.target.value)}
        placeholder="Search models..."
        value={search}
      />

      <div className="flex flex-wrap gap-2">
        <button
          className={cn('rounded-full px-3 py-1 text-xs font-medium transition-colors', !filterProvider ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:bg-accent')}
          onClick={() => setFilterProvider(null)}
          type="button"
        >All</button>
        {modelOptions?.providers?.map(p => (
          <button
            className={cn('rounded-full px-3 py-1 text-xs font-medium transition-colors', filterProvider === p.provider ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:bg-accent')}
            key={p.provider}
            onClick={() => setFilterProvider(filterProvider === p.provider ? null : p.provider ?? null)}
            type="button"
          >{p.name}</button>
        ))}
      </div>

      <div className="space-y-2">
        {filtered.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">No models found</p>
        ) : (
          filtered.map(model => (
            <ModelCard
              key={model.id}
              model={model}
              onFavorite={() => toggleModelFavorite(model.id)}
              onToggle={() => toggleModel(model)}
              selected={state.models.some(m => m.id === model.id)}
            />
          ))
        )}
      </div>
    </div>
  )
}
