import { useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'

import { getGlobalModelOptions, listOAuthProviders } from '@/aetheros'
import { PageShell } from '@/app/page-shell'
import { ModelManager } from '@/app/provider-manager/model-manager'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import {
  type ManagerModel,
  type ManagerProvider,
  setModels,
  setProviders
} from '@/store/provider-manager'
import { setCurrentModel, setCurrentProvider } from '@/store/session'

export function ModelsView() {
  const { data: modelOptions, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['model-options'],
    queryFn: getGlobalModelOptions,
    staleTime: 30000
  })

  const { data: oauthProviders } = useQuery({
    queryKey: ['oauth-providers'],
    queryFn: listOAuthProviders,
    staleTime: 60000
  })

  useEffect(() => {
    if (!modelOptions?.providers) {return}

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
  }, [modelOptions, oauthProviders])

  if (isLoading) {
    return (
      <PageShell>
        <Card className="m-6 p-6" role="status">
          <p className="text-sm font-medium">Loading models…</p>
          <p className="mt-1 text-sm text-(--ui-text-tertiary)">Reading provider availability from the gateway.</p>
        </Card>
      </PageShell>
    )
  }

  if (isError) {
    return (
      <PageShell>
        <Card className="m-6 p-6" role="alert">
          <p className="text-sm font-medium">Models unavailable</p>
          <p className="mt-1 text-sm text-(--ui-text-tertiary)">
            {error instanceof Error ? error.message : 'The gateway did not return model options.'}
          </p>
          <Button className="mt-3" onClick={() => void refetch()} size="sm" variant="outline">
            Retry
          </Button>
        </Card>
      </PageShell>
    )
  }

  return (
    <PageShell>
      <ModelManager />
    </PageShell>
  )
}
