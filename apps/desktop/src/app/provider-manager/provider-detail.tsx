import { useMutation } from '@tanstack/react-query'
import { useCallback, useState } from 'react'

import { validateProviderCredential } from '@/aetheros'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Loader } from '@/components/ui/loader'
import { cn } from '@/lib/utils'
import { startManualLocalEndpoint, startManualProviderOAuth } from '@/store/onboarding'
import type { ManagerModel, ManagerProvider } from '@/store/provider-manager'
import { updateProvider } from '@/store/provider-manager'

const HEALTH_BADGES: Record<string, { label: string; className: string }> = {
  online: { label: 'Online', className: 'bg-green-500/10 text-green-600 border-green-500/30' },
  offline: { label: 'Offline', className: 'bg-red-500/10 text-red-600 border-red-500/30' },
  auth_failed: { label: 'Auth Failed', className: 'bg-yellow-500/10 text-yellow-600 border-yellow-500/30' },
  quota_exceeded: { label: 'Quota Exceeded', className: 'bg-orange-500/10 text-orange-600 border-orange-500/30' },
  slow: { label: 'Slow', className: 'bg-yellow-400/10 text-yellow-600 border-yellow-400/30' },
  unavailable: { label: 'Unavailable', className: 'bg-gray-400/10 text-gray-600 border-gray-400/30' },
  unknown: { label: 'Checking...', className: 'bg-gray-300/10 text-gray-500 border-gray-300/30' }
}

function ModelRow({ model, onAssignRole }: { model: ManagerModel; onAssignRole: (id: string, role: string) => void }) {
  return (
    <div className="flex items-center gap-3 rounded-lg border px-4 py-2.5 text-sm">
      <div className={cn('h-2 w-2 rounded-full', model.speed === 'fast' ? 'bg-green-500' : model.capabilities.reasoning ? 'bg-purple-500' : 'bg-blue-500')} />
      <span className="flex-1 font-mono">{model.name.split('/').pop()}</span>
      {model.pricing?.free && <Badge className="text-[10px] h-5 border-green-500/30 text-green-600" variant="outline">Free</Badge>}
      {model.pricing && !model.pricing.free && (
        <span className="text-xs text-muted-foreground">${model.pricing.input}/M</span>
      )}
      {model.capabilities.vision && <Badge className="text-[10px] h-5" variant="secondary">Vision</Badge>}
      {model.capabilities.reasoning && <Badge className="text-[10px] h-5" variant="secondary">Reasoning</Badge>}
    </div>
  )
}

interface ProviderDetailProps {
  provider: ManagerProvider
  models: ManagerModel[]
  onBack: () => void
  onMainModelChanged?: (provider: string, model: string) => void
}

export function ProviderDetail({ provider, models, onBack, onMainModelChanged }: ProviderDetailProps) {
  const [apiKey, setApiKey] = useState('')
  const [baseUrl, setBaseUrl] = useState(provider.baseUrl ?? '')
  const [showKey, setShowKey] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<string | null>(null)

  const healthBadge = HEALTH_BADGES[provider.health] || HEALTH_BADGES.unknown

  const validateMutation = useMutation({
    mutationFn: async () => {
      if (!apiKey.trim()) {throw new Error('API key required')}

      return validateProviderCredential(provider.keyEnv ?? provider.slug, apiKey, apiKey)
    },
    onSuccess: (result) => {
      updateProvider(provider.slug, { authenticated: true, connected: true, health: 'online' })
      setTestResult('Connection successful')
    },
    onError: (err: Error) => {
      setTestResult(`Failed: ${err.message}`)
    }
  })

  const runHealthCheck = useCallback(async () => {
    setTesting(true)
    setTestResult(null)
    // Simulate health check - in production this would call a backend endpoint
    await new Promise(r => setTimeout(r, 1000))
    updateProvider(provider.slug, { health: provider.authenticated ? 'online' : 'auth_failed' })
    setTesting(false)
  }, [provider.slug, provider.authenticated])

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <header className="flex shrink-0 items-center gap-3 border-b px-6 py-3">
        <button className="text-muted-foreground hover:text-foreground" onClick={onBack} type="button">
          <svg className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path d="M19 12H5M12 19l-7-7 7-7" />
          </svg>
        </button>
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-primary/20 to-primary/5 ring-1 ring-primary/20">
          <span className="text-xs font-bold">{provider.name.slice(0, 2).toUpperCase()}</span>
        </div>
        <div className="flex-1">
          <h2 className="font-semibold">{provider.name}</h2>
          <p className="text-xs text-muted-foreground">{provider.slug} · {provider.modelCount} models</p>
        </div>
        <Badge className={cn('border', healthBadge.className)}>{healthBadge.label}</Badge>
      </header>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto grid max-w-4xl grid-cols-3 gap-6">
          <div className="col-span-2 space-y-6">
            <div className="rounded-xl border p-5">
              <h3 className="mb-4 text-sm font-medium text-muted-foreground uppercase tracking-wider">Authentication</h3>
              {provider.authType === 'api_key' ? (
                <div className="space-y-3">
                  <div className="space-y-2">
                    <Label>API Key</Label>
                    <div className="flex gap-2">
                      <Input
                        className="flex-1 font-mono text-sm"
                        onChange={e => setApiKey(e.target.value)}
                        placeholder={provider.authenticated ? '••••••••••' : 'sk-...'}
                        type={showKey ? 'text' : 'password'}
                        value={apiKey}
                      />
                      <Button aria-label={showKey ? 'Hide API key' : 'Show API key'} className="shrink-0" onClick={() => setShowKey(!showKey)} size="icon" variant="outline">
                        <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                          {showKey ? <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24" /> : <path d="M1 1l22 22M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24" />}
                        </svg>
                      </Button>
                    </div>
                  </div>
                  <Button
                    className="w-full"
                    disabled={!apiKey.trim() || validateMutation.isPending}
                    onClick={() => validateMutation.mutate()}
                  >
                    {validateMutation.isPending ? 'Validating...' : provider.authenticated ? 'Update Key' : 'Connect'}
                  </Button>
                  {testResult && (
                    <p className={cn('text-sm', testResult.includes('successful') ? 'text-green-600' : 'text-destructive')}>{testResult}</p>
                  )}
                </div>
              ) : provider.authType === 'oauth' ? (
                <div className="space-y-3">
                  <p className="text-sm text-muted-foreground">This provider uses OAuth authentication.</p>
                  <Button className="w-full" onClick={() => startManualProviderOAuth(provider.slug)} variant="default">
                    Sign in with {provider.name}
                  </Button>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="space-y-2">
                    <Label>Base URL</Label>
                    <Input
                      className="font-mono text-sm"
                      onChange={e => setBaseUrl(e.target.value)}
                      placeholder={provider.slug === 'ollama' ? 'http://127.0.0.1:11434' : 'http://127.0.0.1:8000/v1'}
                      value={baseUrl}
                    />
                  </div>
                  <Button className="w-full" onClick={() => startManualLocalEndpoint()}>Connect</Button>
                </div>
              )}
            </div>

            <div className="rounded-xl border p-5">
              <div className="mb-4 flex items-center justify-between">
                <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Models ({models.length})</h3>
                {onMainModelChanged && (
                  <Button size="sm" variant="outline">Set as Default</Button>
                )}
              </div>
              <div className="space-y-2">
                {models.slice(0, 20).map(m => <ModelRow key={m.id} model={m} onAssignRole={() => {}} />)}
                {models.length > 20 && (
                  <p className="pt-2 text-center text-xs text-muted-foreground">+{models.length - 20} more models</p>
                )}
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="rounded-xl border p-5">
              <h3 className="mb-4 text-sm font-medium text-muted-foreground uppercase tracking-wider">Health</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Status</span>
                  <Badge className={cn('border', healthBadge.className)}>{healthBadge.label}</Badge>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Latency</span>
                  <span className="font-mono">{provider.latencyMs ? `${provider.latencyMs}ms` : '—'}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Last Sync</span>
                  <span className="text-xs">{provider.lastSync ?? 'Never'}</span>
                </div>
                <Button className="w-full" disabled={testing} onClick={runHealthCheck} size="sm" variant="outline">
                  {testing ? <Loader className="mr-2 h-3 w-3" /> : null}
                  {testing ? 'Checking...' : 'Run Health Check'}
                </Button>
              </div>
            </div>

            {provider.usage && (
              <div className="rounded-xl border p-5">
                <h3 className="mb-4 text-sm font-medium text-muted-foreground uppercase tracking-wider">Usage</h3>
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Today</span>
                    <span className="font-mono">{(provider.usage.dailyTokens / 1000).toFixed(0)}K tokens</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">This Month</span>
                    <span className="font-mono">{(provider.usage.monthlyTokens / 1000000).toFixed(1)}M tokens</span>
                  </div>
                  {provider.usage.creditsRemaining !== null && (
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">Credits</span>
                      <span className="font-mono">${provider.usage.creditsRemaining.toFixed(2)}</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            <div className="rounded-xl border p-5">
              <h3 className="mb-4 text-sm font-medium text-muted-foreground uppercase tracking-wider">Details</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between"><span className="text-muted-foreground">Type</span><span className="capitalize">{provider.category}</span></div>
                <div className="flex justify-between"><span className="text-muted-foreground">Auth</span><span className="capitalize">{provider.authType.replace('_', ' ')}</span></div>
                <div className="flex justify-between"><span className="text-muted-foreground">Version</span><span>{provider.version ?? '—'}</span></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
