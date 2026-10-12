import { useStore } from '@nanostores/react'
import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'

import { getGlobalModelOptions } from '@/aetheros'
import { Checkbox } from '@/components/ui/checkbox'
import { Loader } from '@/components/ui/loader'
import { cn } from '@/lib/utils'
import { $setupWizard, addProvider, removeProvider } from '@/store/setup-wizard'
import type { WizardProvider } from '@/store/setup-wizard'

const PROVIDER_ICONS: Record<string, string> = {
  openai: 'O',
  anthropic: 'A',
  gemini: 'G',
  openrouter: 'OR',
  azure: 'Az',
  ollama: 'Ol',
  'lm-studio': 'LM',
  deepseek: 'DS',
  qwen: 'Q',
  mistral: 'Mi',
  groq: 'Gr',
  'together-ai': 'TA',
  'fireworks-ai': 'FA',
  cerebras: 'C',
  xai: 'X',
  custom: 'Cu'
}

const PROVIDER_GRADIENTS: Record<string, string> = {
  openai: 'from-emerald-500/20 to-emerald-500/5',
  anthropic: 'from-amber-500/20 to-amber-500/5',
  gemini: 'from-blue-500/20 to-blue-500/5',
  openrouter: 'from-purple-500/20 to-purple-500/5',
  azure: 'from-sky-500/20 to-sky-500/5',
  ollama: 'from-orange-500/20 to-orange-500/5',
  deepseek: 'from-cyan-500/20 to-cyan-500/5',
  mistral: 'from-rose-500/20 to-rose-500/5',
  groq: 'from-green-500/20 to-green-500/5',
  xai: 'from-violet-500/20 to-violet-500/5'
}

export function ProvidersStep() {
  const state = useStore($setupWizard)
  const selectedSlugs = new Set(state.providers.map(p => p.slug))

  const { data: modelOptions, isLoading } = useQuery({
    queryKey: ['model-options'],
    queryFn: getGlobalModelOptions,
    staleTime: 60000
  })

  const providers = useMemo(() => {
    if (!modelOptions?.providers) {return []}

    return modelOptions.providers.map(p => ({
      slug: p.provider ?? '',
      name: p.name,
      authType: (p.auth_type === 'oauth' ? 'oauth' : 'api_key') as 'api_key' | 'oauth',
      authenticated: !!p.authenticated,
      models: (p.models || []).map(m => ({
        id: m,
        name: m,
        favorite: false,
        isDefault: false,
        isCoding: false,
        isReasoning: false,
        isFast: false,
        isVision: false,
        isLongContext: false
      }))
    }))
  }, [modelOptions])

  const knownSlugs = new Set(providers.map(p => p.slug))
  const customProviders = state.providers.filter(p => !knownSlugs.has(p.slug))

  const toggleProvider = (provider: WizardProvider) => {
    if (selectedSlugs.has(provider.slug)) {
      removeProvider(provider.slug)
    } else {
      addProvider(provider)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader className="h-8 w-8" />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-2xl space-y-8 py-8">
      <div>
        <h2 className="text-2xl font-semibold">AI Providers</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Select one or more AI providers. You can add more later.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {providers.map(provider => {
          const selected = selectedSlugs.has(provider.slug)
          const gradient = PROVIDER_GRADIENTS[provider.slug] || 'from-gray-500/20 to-gray-500/5'

          return (
            <button
              className={cn(
                'group relative flex items-center gap-3 rounded-xl border p-4 text-left transition-all',
                selected
                  ? 'border-primary/50 bg-primary/5 ring-1 ring-primary/20'
                  : 'border-border hover:border-muted-foreground/30 hover:bg-accent/50'
              )}
              key={provider.slug}
              onClick={() => toggleProvider(provider)}
              type="button"
            >
              <Checkbox checked={selected} className="shrink-0" />
              <div className={cn('flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br ring-1 ring-white/10', gradient)}>
                <span className="text-xs font-bold text-foreground/80">{PROVIDER_ICONS[provider.slug] || provider.slug.slice(0, 2).toUpperCase()}</span>
              </div>
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-medium">{provider.name}</div>
                <div className="text-xs text-muted-foreground capitalize">{provider.authType === 'oauth' ? 'OAuth' : 'API Key'}</div>
              </div>
            </button>
          )
        })}
      </div>

      {customProviders.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-muted-foreground">Custom Providers</h3>
          <div className="grid grid-cols-2 gap-3">
            {customProviders.map(provider => (
              <button
                className="group relative flex items-center gap-3 rounded-xl border border-border p-4 text-left transition-all hover:border-destructive/50 hover:bg-destructive/5"
                key={provider.slug}
                onClick={() => removeProvider(provider.slug)}
                type="button"
              >
                <Checkbox checked={true} className="shrink-0" />
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-gray-500/20 to-gray-500/5 ring-1 ring-white/10">
                  <span className="text-xs font-bold">Cu</span>
                </div>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-medium">{provider.name}</div>
                  <div className="text-xs text-muted-foreground">API Key · {provider.models.length} models</div>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
