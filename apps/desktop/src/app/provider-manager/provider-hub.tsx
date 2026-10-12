import { useMemo } from 'react'

import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'
import type { ManagerProvider } from '@/store/provider-manager'

const PROVIDER_GRADIENTS: Record<string, string> = {
  openai: 'from-emerald-500/20 to-emerald-500/5 ring-emerald-500/20',
  anthropic: 'from-amber-500/20 to-amber-500/5 ring-amber-500/20',
  gemini: 'from-blue-500/20 to-blue-500/5 ring-blue-500/20',
  openrouter: 'from-purple-500/20 to-purple-500/5 ring-purple-500/20',
  'azure-openai': 'from-sky-500/20 to-sky-500/5 ring-sky-500/20',
  deepseek: 'from-cyan-500/20 to-cyan-500/5 ring-cyan-500/20',
  mistral: 'from-rose-500/20 to-rose-500/5 ring-rose-500/20',
  groq: 'from-green-500/20 to-green-500/5 ring-green-500/20',
  'fireworks-ai': 'from-orange-500/20 to-orange-500/5 ring-orange-500/20',
  'together-ai': 'from-violet-500/20 to-violet-500/5 ring-violet-500/20',
  cerebras: 'from-yellow-500/20 to-yellow-500/5 ring-yellow-500/20',
  cohere: 'from-blue-600/20 to-blue-600/5 ring-blue-600/20',
  xai: 'from-fuchsia-500/20 to-fuchsia-500/5 ring-fuchsia-500/20',
  perplexity: 'from-indigo-500/20 to-indigo-500/5 ring-indigo-500/20',
  'hugging-face': 'from-yellow-600/20 to-yellow-600/5 ring-yellow-600/20',
  ollama: 'from-orange-600/20 to-orange-600/5 ring-orange-600/20',
  'lm-studio': 'from-gray-500/20 to-gray-500/5 ring-gray-500/20'
}

const PROVIDER_LOGOS: Record<string, string> = {
  openai: 'O',
  anthropic: 'A',
  gemini: 'Gm',
  openrouter: 'OR',
  'azure-openai': 'Az',
  deepseek: 'DS',
  mistral: 'Mi',
  groq: 'Gr',
  'fireworks-ai': 'FA',
  'together-ai': 'TA',
  cerebras: 'C',
  cohere: 'Co',
  xai: 'X',
  perplexity: 'Px',
  'hugging-face': 'HF',
  ollama: 'Ol',
  'lm-studio': 'LM',
  vllm: 'vL',
  'llama-cpp': 'lCP',
  'text-generation-webui': 'TG',
  koboldcpp: 'KC',
  local: 'Cu'
}

const HEALTH_COLORS: Record<string, string> = {
  online: 'bg-green-500',
  offline: 'bg-red-500',
  auth_failed: 'bg-yellow-500',
  quota_exceeded: 'bg-orange-500',
  slow: 'bg-yellow-400',
  unavailable: 'bg-gray-400',
  unknown: 'bg-gray-300'
}

function ProviderCard({ provider, onSelect }: { provider: ManagerProvider; onSelect: () => void }) {
  const gradient = PROVIDER_GRADIENTS[provider.slug] || 'from-gray-500/20 to-gray-500/5 ring-gray-500/20'
  const logo = PROVIDER_LOGOS[provider.slug] || provider.slug.slice(0, 2).toUpperCase()

  return (
    <button className="group relative flex flex-col gap-3 rounded-xl border bg-card p-5 text-left transition-all hover:border-muted-foreground/30 hover:shadow-sm" onClick={onSelect} type="button">
      <div className="flex items-start justify-between">
        <div className={cn('flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br ring-1', gradient)}>
          <span className="text-sm font-bold text-foreground/80">{logo}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className={cn('h-2 w-2 rounded-full', HEALTH_COLORS[provider.health] || HEALTH_COLORS.unknown)} />
          <span className="text-xs text-muted-foreground capitalize">{provider.health === 'unknown' ? (provider.authenticated ? 'connected' : 'disconnected') : provider.health}</span>
        </div>
      </div>

      <div>
        <h3 className="font-medium">{provider.name}</h3>
        <p className="mt-0.5 text-xs text-muted-foreground">{provider.modelCount} models</p>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {provider.authenticated ? (
          <Badge className="border-green-500/30 text-green-600 text-[10px] h-5" variant="outline">Connected</Badge>
        ) : (
          <Badge className="text-[10px] h-5" variant="outline">Not connected</Badge>
        )}
        {provider.category === 'local' && (
          <Badge className="text-[10px] h-5" variant="secondary">Local</Badge>
        )}
        {provider.authType === 'oauth' && (
          <Badge className="text-[10px] h-5" variant="outline">OAuth</Badge>
        )}
      </div>

      {provider.usage && (
        <div className="mt-1 space-y-1 text-xs text-muted-foreground">
          <div className="flex justify-between"><span>Today</span><span>{(provider.usage.dailyTokens / 1000).toFixed(0)}K tokens</span></div>
          {provider.usage.creditsRemaining !== null && (
            <div className="flex justify-between"><span>Credits</span><span>${provider.usage.creditsRemaining.toFixed(2)}</span></div>
          )}
        </div>
      )}
    </button>
  )
}

function ProviderSection({ title, providers, onSelect }: { title: string; providers: ManagerProvider[]; onSelect: (slug: string) => void }) {
  if (providers.length === 0) {return null}

  return (
    <div className="space-y-3">
      <h2 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">{title}</h2>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-3 xl:grid-cols-4">
        {providers.map(p => <ProviderCard key={p.slug} onSelect={() => onSelect(p.slug)} provider={p} />)}
      </div>
    </div>
  )
}

interface ProviderHubProps {
  providers: ManagerProvider[]
  search: string
  onSearchChange: (q: string) => void
  onSelectProvider: (slug: string) => void
}

export function ProviderHub({ providers, search, onSearchChange, onSelectProvider }: ProviderHubProps) {
  const filtered = useMemo(() => {
    if (!search.trim()) {return providers}
    const q = search.toLowerCase()

    return providers.filter(p => p.name.toLowerCase().includes(q) || p.slug.toLowerCase().includes(q))
  }, [providers, search])

  const cloud = filtered.filter(p => p.category === 'cloud')
  const local = filtered.filter(p => p.category === 'local')
  const custom = filtered.filter(p => p.category === 'custom')

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="mb-6">
        <Input
          className="max-w-md font-mono text-sm"
          onChange={e => onSearchChange(e.target.value)}
          placeholder="Search providers..."
          value={search}
        />
      </div>

      <div className="space-y-8">
        <ProviderSection onSelect={onSelectProvider} providers={cloud} title="Cloud Providers" />
        <ProviderSection onSelect={onSelectProvider} providers={local} title="Local Providers" />
        <ProviderSection onSelect={onSelectProvider} providers={custom} title="Custom & Compatible" />
      </div>

      {filtered.length === 0 && (
        <p className="py-12 text-center text-sm text-muted-foreground">No providers found</p>
      )}
    </div>
  )
}
