import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { Input } from '@/components/ui/input'
import {
  Check,
  Loader2,
  Settings
} from '@/lib/icons'
import { cn } from '@/lib/utils'


// =============================================================================
// Types
// =============================================================================

export interface ManagedProvider {
  id: string
  name: string
  slug: string
  model: string
  models: string[]
  status: 'connected' | 'error' | 'unconfigured'
  apiKey: string
  isDefault: boolean
  latency?: string
  lastTested?: string
}

interface ModelManagerProps {
  providers: ManagedProvider[]
  onAdd: () => void
  onEdit: (id: string) => void
  onDelete: (id: string) => void
  onDuplicate: (id: string) => void
  onTest: (id: string) => Promise<{ ok: boolean; latency?: string }>
  onSetDefault: (id: string) => void
  onExport: () => void
  onImport: () => void
  onRefresh: () => void
}

// =============================================================================
// Model Manager Component
// =============================================================================

export function ModelManager({
  providers,
  onAdd,
  onEdit,
  onDelete,
  onDuplicate,
  onTest,
  onSetDefault,
  onExport,
  onImport,
  onRefresh
}: ModelManagerProps) {
  const [search, setSearch] = useState('')
  const [testingId, setTestingId] = useState<string | null>(null)
  const [menuOpen, setMenuOpen] = useState<string | null>(null)

  const filtered = search.trim()
    ? providers.filter(p =>
        p.name.toLowerCase().includes(search.toLowerCase()) ||
        p.model.toLowerCase().includes(search.toLowerCase()) ||
        p.slug.toLowerCase().includes(search.toLowerCase())
      )
    : providers

  const handleTest = async (id: string) => {
    setTestingId(id)
    await onTest(id)
    setTestingId(null)
  }

  // Empty state — no providers configured
  if (providers.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[40dvh] text-center gap-6 px-6">          <div className="flex size-16 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500/20 via-cyan-400/10 to-purple-500/20">
          <Settings className="size-7 text-muted-foreground" />
        </div>
        <div className="space-y-2">
          <h2 className="text-xl font-semibold tracking-tight">No AI provider configured.</h2>
          <p className="text-sm text-muted-foreground max-w-sm mx-auto">
            Connect an AI provider to start using AetherOS. You can add multiple providers and switch between them anytime.
          </p>
        </div>
        <Button className="px-8 gap-2" onClick={onAdd} size="lg">
          <Codicon className="size-4" name="add" />
          Configure Provider
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="relative flex-1 max-w-xs">
          <Codicon className="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" name="search" />
          <Input
            className="pl-8 h-9 text-sm"
            onChange={e => setSearch(e.target.value)}
            placeholder="Search providers and models..."
            value={search}
          />
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={onRefresh} size="sm" variant="ghost">
            <Codicon className="size-4" name="refresh" />
          </Button>
          <Button onClick={onImport} size="sm" variant="ghost">
            <Codicon className="size-4" name="cloud-download" />
            Import
          </Button>
          <Button onClick={onExport} size="sm" variant="ghost">
            <Codicon className="size-4" name="cloud-upload" />
            Export
          </Button>
          <Button onClick={onAdd} size="sm">
            <Codicon className="size-4 mr-1" name="add" />
            Add Provider
          </Button>
        </div>
      </div>

      {/* Provider table */}
      <div className="overflow-hidden rounded-lg border border-border">
        {/* Table header */}
        <div className="grid grid-cols-[1fr_1.5fr_100px_1fr_60px_80px_60px] gap-2 bg-muted/30 px-4 py-2.5 text-xs font-medium uppercase tracking-wider text-muted-foreground">
          <span>Provider</span>
          <span>Model</span>
          <span>Status</span>
          <span>API Key</span>
          <span>Default</span>
          <span>Latency</span>
          <span className="text-right">Actions</span>
        </div>

        {/* Table rows */}
        <div className="divide-y divide-border">
          {filtered.length === 0 ? (
            <div className="px-4 py-8 text-center text-sm text-muted-foreground">
              No providers match your search.
            </div>
          ) : (
            filtered.map(provider => (
              <div className="group grid grid-cols-[1fr_1.5fr_100px_1fr_60px_80px_60px] gap-2 items-center px-4 py-3 text-sm transition-colors hover:bg-muted/20" key={provider.id}>
                {/* Provider */}
                <div className="flex items-center gap-2 min-w-0">
                  <div className={cn(
                    'flex size-7 items-center justify-center rounded-md text-xs font-bold shrink-0',
                    provider.status === 'connected'
                      ? 'bg-emerald-500/20 text-emerald-600'
                      : provider.status === 'error'
                      ? 'bg-destructive/20 text-destructive'
                      : 'bg-muted text-muted-foreground'
                  )}>
                    {provider.name.charAt(0)}
                  </div>
                  <div className="min-w-0">
                    <p className="truncate font-medium">{provider.name}</p>
                    <p className="truncate text-xs text-muted-foreground">{provider.slug}</p>
                  </div>
                </div>

                {/* Model */}
                <div className="min-w-0">
                  {provider.status === 'connected' ? (
                    <>
                      <p className="truncate font-mono text-xs">{provider.model}</p>
                      <p className="text-xs text-muted-foreground">{provider.models.length} models available</p>
                    </>
                  ) : (
                    <span className="text-xs text-muted-foreground">—</span>
                  )}
                </div>

                {/* Status */}
                <div>
                  <span className={cn(
                    'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium',
                    provider.status === 'connected' ? 'bg-emerald-500/10 text-emerald-600' :
                    provider.status === 'error' ? 'bg-destructive/10 text-destructive' :
                    'bg-muted text-muted-foreground'
                  )}>
                    {provider.status === 'connected' && <Check className="size-3" />}
                    {provider.status === 'connected' ? 'Connected' :
                     provider.status === 'error' ? 'Error' : 'Offline'}
                  </span>
                </div>

                {/* API Key */}
                <div className="min-w-0">
                  {provider.apiKey ? (
                    <span className="font-mono text-xs text-muted-foreground">
                      {provider.apiKey.slice(0, 8)}...
                    </span>
                  ) : (
                    <span className="text-xs text-muted-foreground">—</span>
                  )}
                </div>

                {/* Default */}
                <div>
                  {provider.isDefault ? (
                    <span className="inline-flex items-center gap-1 text-xs font-medium text-primary">
                      <Check className="size-3" />
                      Active
                    </span>
                  ) : (
                    <Button
                      className="text-xs text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={() => onSetDefault(provider.id)}
                      size="xs"
                      variant="ghost"
                    >
                      Set
                    </Button>
                  )}
                </div>

                {/* Latency */}
                <div className="text-xs text-muted-foreground">
                  {provider.latency || '—'}
                </div>

                {/* Actions */}
                <div className="flex items-center justify-end gap-1">
                  <Button
                    className="opacity-0 group-hover:opacity-100 transition-opacity"
                    disabled={testingId === provider.id || provider.status !== 'connected'}
                    onClick={() => handleTest(provider.id)}
                    size="xs"
                    title="Test connection"
                    variant="ghost"
                  >
                    {testingId === provider.id
                      ? <Loader2 className="size-3.5 animate-spin" />
                      :                      <Codicon className="size-3.5" name="beaker" />
                    }
                  </Button>
                  <div className="relative">
                    <Button
                      className="opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={() => setMenuOpen(menuOpen === provider.id ? null : provider.id)}
                      size="xs"
                      variant="ghost"
                    >
                      <Codicon className="size-3.5" name="kebab-vertical" />
                    </Button>
                    {menuOpen === provider.id && (
                      <>
                        <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(null)} />
                        <div className="absolute right-0 top-full z-20 mt-1 w-44 rounded-lg border border-border bg-popover py-1 shadow-lg">
                          <button
                            className="flex w-full items-center gap-2 px-3 py-1.5 text-xs transition-colors hover:bg-accent"
                            onClick={() => { onEdit(provider.id); setMenuOpen(null) }}
                            type="button"
                          >
                            <Codicon className="size-3.5" name="gear" />
                            Edit
                          </button>
                          <button
                            className="flex w-full items-center gap-2 px-3 py-1.5 text-xs transition-colors hover:bg-accent"
                            onClick={() => { onDuplicate(provider.id); setMenuOpen(null) }}
                            type="button"
                          >
                            <Codicon className="size-3.5" name="copy" />
                            Duplicate
                          </button>
                          <button
                            className="flex w-full items-center gap-2 px-3 py-1.5 text-xs transition-colors hover:bg-accent"
                            disabled={testingId === provider.id}
                            onClick={() => { handleTest(provider.id); setMenuOpen(null) }}
                            type="button"
                          >
                            <Codicon className="size-3.5" name="beaker" />
                            Test Connection
                          </button>
                          <hr className="my-1 border-border" />
                          <button
                            className="flex w-full items-center gap-2 px-3 py-1.5 text-xs text-destructive transition-colors hover:bg-destructive/10"
                            onClick={() => { onDelete(provider.id); setMenuOpen(null) }}
                            type="button"
                          >
                            <Codicon className="size-3.5" name="trash" />
                            Delete
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Summary */}
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>
          {filtered.length} of {providers.length} provider{providers.length !== 1 ? 's' : ''}
        </span>
        <span>
          {providers.filter(p => p.status === 'connected').length} connected
          · {providers.filter(p => p.isDefault).length} default
        </span>
      </div>
    </div>
  )
}
