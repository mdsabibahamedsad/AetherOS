import { useStore } from '@nanostores/react'
import { useMemo } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { cn } from '@/lib/utils'
import {
  $providerManager,
  type ManagerModel,
  type ModelRole,
  ROLE_LABELS,
  setModelFilterProvider,
  setModelFilterRole,
  setModelSort,
  setSearchQuery,
  setShowHiddenModels,
  toggleModelFavorite,
  toggleModelHidden,
  toggleModelPin,
  toggleSortAsc
} from '@/store/provider-manager'

const ROLE_OPTIONS: Array<{ value: ModelRole | 'all'; label: string }> = [
  { value: 'all', label: 'All Roles' },
  ...Object.entries(ROLE_LABELS).map(([key, label]) => ({ value: key as ModelRole, label }))
]

function ModelTableRow({ model, onFavorite, onPin, onHide }: {
  model: ManagerModel
  onFavorite: () => void
  onPin: () => void
  onHide: () => void
}) {
  return (
    <div className={cn(
      'flex items-center gap-3 rounded-lg border px-4 py-2.5 text-sm transition-all hover:bg-accent/30',
      model.hidden && 'opacity-40'
    )}>
      <button className="shrink-0 text-muted-foreground hover:text-yellow-500" onClick={onFavorite} type="button">
        <svg className={cn('h-4 w-4', model.favorite && 'fill-yellow-500 text-yellow-500')} fill={model.favorite ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
          <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
        </svg>
      </button>

      <button className={cn('shrink-0 text-muted-foreground hover:text-blue-500', model.pinned && 'text-blue-500')} onClick={onPin} type="button">
        <svg className="h-4 w-4 rotate-45" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
          <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2z" />
        </svg>
      </button>

      <div className={cn('h-2 w-2 shrink-0 rounded-full', model.speed === 'fast' ? 'bg-green-500' : model.capabilities.reasoning ? 'bg-purple-500' : 'bg-blue-400')} />

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm truncate">{model.name}</span>
          {model.pricing?.free && <Badge className="text-[10px] h-5 border-green-500/30 text-green-600 shrink-0" variant="outline">Free</Badge>}
        </div>
        <span className="text-xs text-muted-foreground">{model.providerName}</span>
      </div>

      <div className="flex items-center gap-1.5">
        {model.capabilities.vision && <Badge className="text-[10px] h-5" variant="secondary">Vision</Badge>}
        {model.capabilities.reasoning && <Badge className="text-[10px] h-5" variant="secondary">Reason</Badge>}
        {model.capabilities.functionCalling && <Badge className="text-[10px] h-5" variant="outline">FC</Badge>}
      </div>

      {model.pricing && !model.pricing.free && (
        <span className="shrink-0 text-xs text-muted-foreground font-mono">${model.pricing.input}/M</span>
      )}

      {model.contextLength && (
        <span className="shrink-0 text-xs text-muted-foreground font-mono">{(model.contextLength / 1000).toFixed(0)}K</span>
      )}

      <div className="flex items-center gap-1">
        {model.roles.slice(0, 2).map(role => (
          <Badge className="text-[10px] h-5" key={role} variant="secondary">{ROLE_LABELS[role]}</Badge>
        ))}
      </div>

      <button className="shrink-0 text-muted-foreground/50 hover:text-destructive" onClick={onHide} type="button">
        <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
          <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24" />
        </svg>
      </button>
    </div>
  )
}

export function ModelManager() {
  const state = useStore($providerManager)

  const providers = useMemo(() => {
    const seen = new Set<string>()

    return state.models
      .map(m => ({ slug: m.provider, name: m.providerName }))
      .filter(p => { const k = p.slug;

 if (seen.has(k)) {return false;} seen.add(k);

 return true })
      .sort((a, b) => a.name.localeCompare(b.name))
  }, [state.models])

  const filtered = useMemo(() => {
    let list = [...state.models]

    if (state.searchQuery) {
      const q = state.searchQuery.toLowerCase()
      list = list.filter(m => m.name.toLowerCase().includes(q) || m.providerName.toLowerCase().includes(q))
    }

    if (state.modelFilterProvider) {
      list = list.filter(m => m.provider === state.modelFilterProvider)
    }

    if (state.modelFilterRole) {
      list = list.filter(m => m.roles.includes(state.modelFilterRole!))
    }

    if (!state.showHiddenModels) {
      list = list.filter(m => !m.hidden)
    }

    const sortKey = state.modelSort
    list.sort((a, b) => {
      let cmp = 0

      if (sortKey === 'name') {cmp = a.name.localeCompare(b.name)}
      else if (sortKey === 'provider') {cmp = a.providerName.localeCompare(b.providerName)}
      else if (sortKey === 'context') {cmp = (a.contextLength ?? 0) - (b.contextLength ?? 0)}
      else if (sortKey === 'latency') {cmp = (a.latencyMs ?? 999999) - (b.latencyMs ?? 999999)}

      return state.sortAsc ? cmp : -cmp
    })

    return list
  }, [state.models, state.searchQuery, state.modelFilterProvider, state.modelFilterRole, state.modelSort, state.sortAsc, state.showHiddenModels])

  const modelCount = filtered.length
  const favoriteCount = filtered.filter(m => m.favorite).length
  const pinnedCount = filtered.filter(m => m.pinned).length

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="flex shrink-0 items-center gap-3 border-b px-6 py-3">
        <Input
          className="max-w-xs font-mono text-sm"
          onChange={e => setSearchQuery(e.target.value)}
          placeholder="Search models..."
          value={state.searchQuery}
        />
        <Select onValueChange={v => setModelFilterProvider(v === 'all' ? null : v)} value={state.modelFilterProvider ?? 'all'}>
          <SelectTrigger className="w-40"><SelectValue placeholder="All providers" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Providers</SelectItem>
            {providers.map(p => <SelectItem key={p.slug} value={p.slug}>{p.name}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select onValueChange={v => setModelFilterRole(v === 'all' ? null : v as ModelRole)} value={state.modelFilterRole ?? 'all'}>
          <SelectTrigger className="w-36"><SelectValue placeholder="All roles" /></SelectTrigger>
          <SelectContent>
            {ROLE_OPTIONS.map(o => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select onValueChange={v => setModelSort(v as 'name' | 'provider' | 'context' | 'latency')} value={state.modelSort}>
          <SelectTrigger className="w-32"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="name">Name</SelectItem>
            <SelectItem value="provider">Provider</SelectItem>
            <SelectItem value="context">Context</SelectItem>
            <SelectItem value="latency">Latency</SelectItem>
          </SelectContent>
        </Select>
        <Button aria-label="Toggle sort order" className="shrink-0" onClick={toggleSortAsc} size="icon" variant="ghost">
          <svg className={cn('h-4 w-4 transition-transform', !state.sortAsc && 'rotate-180')} fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path d="M8 3v12M12 3l-4 4M8 7l-4-4M16 21V9M16 17l-4 4M20 17l-4-4" />
          </svg>
        </Button>
        <div className="ml-auto flex items-center gap-3 text-xs text-muted-foreground">
          <span>{modelCount} models</span>
          {favoriteCount > 0 && <span>{favoriteCount} ★</span>}
          {pinnedCount > 0 && <span>{pinnedCount} 📌</span>}
          <label className="flex items-center gap-1.5 cursor-pointer">
            <input checked={state.showHiddenModels} className="rounded" onChange={e => setShowHiddenModels(e.target.checked)} type="checkbox" />
            Show hidden
          </label>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <div className="space-y-1.5">
          {filtered.length === 0 ? (
            <p className="py-12 text-center text-sm text-muted-foreground">No models match your filters</p>
          ) : (
            filtered.map(model => (
              <ModelTableRow
                key={model.id}
                model={model}
                onFavorite={() => toggleModelFavorite(model.id)}
                onHide={() => toggleModelHidden(model.id)}
                onPin={() => toggleModelPin(model.id)}
              />
            ))
          )}
        </div>
      </div>
    </div>
  )
}
