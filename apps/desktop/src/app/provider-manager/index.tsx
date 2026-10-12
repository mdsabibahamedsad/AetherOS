import { useStore } from '@nanostores/react'
import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import { getEnvVars, getGlobalModelOptions, listOAuthProviders } from '@/aetheros'
import { getAuxiliaryModels } from '@/aetheros'
import { cn } from '@/lib/utils'
import { $providerManager, type ManagerModel, type ManagerProvider, setModels, setProviders, setSelectedProvider } from '@/store/provider-manager'
import { setCurrentModel, setCurrentProvider } from '@/store/session'

import { HealthMonitor } from './health-monitor'
import { ModelManager } from './model-manager'
import { ModelRouter } from './model-router'
import { ModelTester } from './model-tester'
import { ProviderDetail } from './provider-detail'
import { ProviderHub } from './provider-hub'
import { ProviderSettings } from './settings'
import { UsageDashboard } from './usage-dashboard'

const TABS = [
  { id: 'hub', label: 'Providers', icon: '☁' },
  { id: 'models', label: 'Models', icon: '🧠' },
  { id: 'router', label: 'Router', icon: '↗' },
  { id: 'health', label: 'Health', icon: '♥' },
  { id: 'tester', label: 'Tester', icon: '▶' },
  { id: 'usage', label: 'Usage', icon: '📊' },
  { id: 'settings', label: 'Settings', icon: '⚙' }
] as const

type TabId = (typeof TABS)[number]['id']

interface ProviderManagerViewProps {
  gateway?: unknown
  onClose?: () => void
  onMainModelChanged?: (provider: string, model: string) => void
}

export function ProviderManagerView({ onClose, onMainModelChanged }: ProviderManagerViewProps) {
  const state = useStore($providerManager)
  const [activeTab, setActiveTab] = useState<TabId>('hub')
  const [searchQuery, setSearchQuery] = useState('')

  const { data: modelOptions } = useQuery({
    queryKey: ['model-options'],
    queryFn: getGlobalModelOptions,
    staleTime: 30000
  })

  const { data: envVars } = useQuery({
    queryKey: ['env-vars'],
    queryFn: getEnvVars,
    staleTime: 30000
  })

  const { data: auxModels } = useQuery({
    queryKey: ['auxiliary-models'],
    queryFn: getAuxiliaryModels,
    staleTime: 30000
  })

  const { data: oauthProviders } = useQuery({
    queryKey: ['oauth-providers'],
    queryFn: listOAuthProviders,
    staleTime: 60000
  })

  useEffect(() => {
    if (!modelOptions?.providers) {return}

    const envMap = new Map(Object.entries(envVars ?? {}))
    const oauthSet = new Set((oauthProviders?.providers ?? []).map((p: { id: string }) => p.id))

    const providers: ManagerProvider[] = modelOptions.providers.map(p => {
      const slug = p.provider ?? ''
      const isLocal = ['ollama', 'lm-studio', 'vllm', 'llama-cpp', 'text-generation-webui', 'koboldcpp', 'local'].includes(slug)
      const isCustom = p.auth_type === 'api_key' && !p.is_current && !isLocal && !oauthSet.has(slug)

      return {
        slug,
        name: p.name,
        category: isLocal ? 'local' as const : isCustom ? 'custom' as const : 'cloud' as const,
        authType: (p.auth_type as ManagerProvider['authType']) || 'api_key',
        authenticated: !!p.authenticated,
        connected: !!p.authenticated,
        health: 'unknown' as const,
        latencyMs: null,
        modelCount: p.models?.length ?? 0,
        version: null,
        lastSync: null,
        usage: null,
        capabilities: [],
        keyEnv: p.key_env ?? null,
        baseUrl: null
      }
    })

    setProviders(providers)

    const allModels: ManagerModel[] = []
    const seen = new Set<string>()

    for (const p of modelOptions.providers) {
      const pricing = p.pricing as Record<string, { input: string; output: string; cache: string | null; free: boolean }> | undefined
      const caps = p.capabilities as Record<string, { fast: boolean; reasoning: boolean }> | undefined

      for (const m of (p.models ?? [])) {
        if (!seen.has(m)) {
          seen.add(m)
          const mp = pricing?.[m]
          const mc = caps?.[m]
          allModels.push({
            id: m,
            provider: p.provider ?? '',
            providerName: p.name,
            name: m,
            contextLength: null,
            maxTokens: null,
            pricing: mp ? { input: mp.input ?? '—', output: mp.output ?? '—', cache: mp.cache ?? null, free: mp.free ?? false } : null,
            capabilities: {
              vision: m.toLowerCase().includes('vision'),
              audio: m.toLowerCase().includes('audio'),
              functionCalling: true,
              reasoning: mc?.reasoning ?? m.toLowerCase().includes('reasoning'),
              streaming: true,
              embedding: m.toLowerCase().includes('embedding'),
              toolSupport: true
            },
            favorite: false,
            pinned: false,
            hidden: false,
            roles: [],
            latencyMs: null,
            speed: mc?.fast ? 'fast' as const : null
          })
        }
      }
    }

    setModels(allModels)

    if (modelOptions?.provider && modelOptions?.model) {
      setCurrentProvider(modelOptions.provider)
      setCurrentModel(modelOptions.model)
    } else {
      const currentProv = providers.find(p => p.authenticated)

      if (currentProv) {
        setCurrentProvider(currentProv.slug)

        if (currentProv.modelCount > 0) {
          const firstModel = allModels.find(m => m.provider === currentProv.slug)

          if (firstModel) {setCurrentModel(firstModel.name)}
        }
      }
    }
  }, [modelOptions, envVars, oauthProviders])

  const selectedProvider = state.providers.find(p => p.slug === state.selectedProvider)

  if (state.selectedProvider && selectedProvider && activeTab !== 'settings') {
    return (
      <ProviderDetail
        models={state.models.filter(m => m.provider === state.selectedProvider)}
        onBack={() => setSelectedProvider(null)}
        onMainModelChanged={onMainModelChanged}
        provider={selectedProvider}
      />
    )
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <header className="flex shrink-0 items-center justify-between border-b px-6 py-3">
        <div>
          <h1 className="text-xl font-semibold">AI Providers</h1>
          <p className="text-sm text-muted-foreground">
            {state.providers.filter(p => p.authenticated).length} connected · {state.providers.length} available · {state.models.length} models
          </p>
        </div>
        {onClose && (
          <button className="text-muted-foreground hover:text-foreground" onClick={onClose} type="button">
            <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        )}
      </header>

      <div className="flex shrink-0 items-center gap-1 border-b px-4">
        {TABS.map(tab => (
          <button
            className={cn(
              'flex items-center gap-1.5 border-b-2 px-4 py-3 text-sm font-medium transition-colors',
              activeTab === tab.id ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'
            )}
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            type="button"
          >
            <span className="text-xs">{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'hub' && (activeTab === 'hub' ? (
        <ProviderHub
          onSearchChange={setSearchQuery}
          onSelectProvider={slug => setSelectedProvider(slug)}
          providers={state.providers}
          search={searchQuery}
        />
      ) : null)}
      {activeTab === 'models' && <ModelManager />}
      {activeTab === 'router' && <ModelRouter auxModels={auxModels} />}
      {activeTab === 'health' && <HealthMonitor />}
      {activeTab === 'tester' && <ModelTester />}
      {activeTab === 'usage' && <UsageDashboard />}
      {activeTab === 'settings' && <ProviderSettings />}
    </div>
  )
}
