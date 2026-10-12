import { useStore } from '@nanostores/react'
import { useMemo } from 'react'

import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { cn } from '@/lib/utils'
import { $providerManager, ROUTER_TASKS, updateRouterRule } from '@/store/provider-manager'

const TASK_ICONS: Record<string, string> = {
  default: '💬',
  coding: '</>',
  reasoning: '🧠',
  vision: '👁',
  embedding: '📐',
  voice: '🎤',
  automation: '⚡',
  research: '🔍'
}

interface ModelRouterViewProps {
  auxModels?: unknown
}

export function ModelRouter(_props: ModelRouterViewProps) {
  const state = useStore($providerManager)

  const providerOptions = useMemo(() => {
    const seen = new Set<string>()

    return state.providers
      .filter(p => p.authenticated)
      .map(p => ({ slug: p.slug, name: p.name }))
      .filter(p => { const k = p.slug;

 if (seen.has(k)) {return false;} seen.add(k);

 return true })
  }, [state.providers])

  const getModelsForProvider = (slug: string) =>
    state.models.filter(m => m.provider === slug && !m.hidden)

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="border-b px-6 py-4">
        <h2 className="text-lg font-semibold">Model Router</h2>
        <p className="text-sm text-muted-foreground">Assign default models for different task types</p>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-3xl space-y-4">
          {ROUTER_TASKS.map(task => {
            const rule = state.routerRules.find(r => r.task === task.id)

            if (!rule) {return null}

            const availableModels = rule.provider ? getModelsForProvider(rule.provider) : []
            const selectedModel = availableModels.find(m => m.id === rule.model)

            return (
              <div className={cn('rounded-xl border p-5 transition-all', rule.enabled ? '' : 'opacity-50')} key={task.id}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-lg">{TASK_ICONS[task.id] || '📋'}</span>
                    <div>
                      <h3 className="font-medium">{task.label}</h3>
                      <p className="text-xs text-muted-foreground">
                        {rule.provider && rule.model
                          ? `Routed to ${selectedModel?.name?.split('/').pop() ?? rule.model} via ${state.providers.find(p => p.slug === rule.provider)?.name ?? rule.provider}`
                          : 'No model assigned — uses default chat model'}
                      </p>
                    </div>
                  </div>
                  <Switch checked={rule.enabled} onCheckedChange={v => updateRouterRule(task.id, { enabled: v })} />
                </div>

                {rule.enabled && (
                  <div className="mt-4 grid grid-cols-2 gap-3">
                    <div className="space-y-1.5">
                      <label className="text-xs text-muted-foreground">Provider</label>
                      <Select onValueChange={v => updateRouterRule(task.id, { provider: v || null, model: null })} value={rule.provider ?? ''}>
                        <SelectTrigger><SelectValue placeholder="Auto (use main)" /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="">Auto (use main)</SelectItem>
                          {providerOptions.map(p => <SelectItem key={p.slug} value={p.slug}>{p.name}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-xs text-muted-foreground">Model</label>
                      <Select
                        disabled={!rule.provider}
                        onValueChange={v => updateRouterRule(task.id, { model: v || null })}
                        value={rule.model ?? ''}
                      >
                        <SelectTrigger><SelectValue placeholder={rule.provider ? 'Select model' : 'Select provider first'} /></SelectTrigger>
                        <SelectContent>
                          {availableModels.map(m => (
                            <SelectItem key={m.id} value={m.id}>
                              <span className="flex items-center gap-2">
                                {m.name.split('/').pop()}
                                {m.capabilities.reasoning && <Badge className="text-[10px] h-4" variant="outline">R</Badge>}
                                {m.capabilities.vision && <Badge className="text-[10px] h-4" variant="outline">V</Badge>}
                              </span>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                )}

                {rule.provider && rule.model && (
                  <div className="mt-3 flex items-center gap-2 rounded-lg bg-primary/5 px-3 py-2 text-xs text-muted-foreground">
                    <svg className="h-3.5 w-3.5 shrink-0" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                      <path d="M9 18l6-6-6-6" />
                    </svg>
                    <span className="font-mono">{rule.provider}/{rule.model.split('/').pop()}</span>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
