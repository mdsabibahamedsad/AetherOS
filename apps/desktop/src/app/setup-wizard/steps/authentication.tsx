import { useStore } from '@nanostores/react'
import { useState } from 'react'

import { validateProviderCredential } from '@/aetheros'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Loader } from '@/components/ui/loader'
import { $setupWizard, updateProviderAuth } from '@/store/setup-wizard'

function ApiKeyForm({ slug, name, onValidated }: { slug: string; name: string; onValidated: () => void }) {
  const [key, setKey] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [validating, setValidating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleValidate = async () => {
    if (!key.trim()) {return}
    setValidating(true)
    setError(null)

    try {
      await validateProviderCredential(slug, key, key)
      updateProviderAuth(slug, { apiKey: key, baseUrl: baseUrl || undefined })
      onValidated()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Validation failed')
    } finally {
      setValidating(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label>API Key</Label>
        <Input
          className="font-mono text-sm"
          onChange={e => setKey(e.target.value)}
          placeholder="sk-..."
          type="password"
          value={key}
        />
      </div>

      {slug === 'local' && (
        <div className="space-y-2">
          <Label>Base URL</Label>
          <Input
            className="font-mono text-sm"
            onChange={e => setBaseUrl(e.target.value)}
            placeholder="http://127.0.0.1:8000/v1"
            value={baseUrl}
          />
        </div>
      )}

      {error && <p className="text-sm text-destructive">{error}</p>}

      <Button className="w-full" disabled={!key.trim() || validating} onClick={handleValidate}>
        {validating ? <><Loader className="mr-2 h-4 w-4" /> Validating...</> : `Connect ${name}`}
      </Button>
    </div>
  )
}

export function AuthenticationStep() {
  const state = useStore($setupWizard)

  const [validatedSlugs, setValidatedSlugs] = useState<Set<string>>(new Set(
    state.providers.filter(p => p.authenticated).map(p => p.slug)
  ))

  const unauthenticated = state.providers.filter(p => p.authType === 'api_key' && !validatedSlugs.has(p.slug))
  const authenticated = state.providers.filter(p => p.authType === 'oauth' || validatedSlugs.has(p.slug))

  if (state.providers.length === 0) {
    return (
      <div className="mx-auto max-w-xl py-20 text-center">
        <p className="text-muted-foreground">No providers selected. Go back and select at least one provider.</p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-xl space-y-8 py-8">
      <div>
        <h2 className="text-2xl font-semibold">Authentication</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Enter API keys or configure authentication for your selected providers
        </p>
      </div>

      {unauthenticated.length > 0 && (
        <div className="space-y-6">
          <h3 className="text-sm font-medium text-muted-foreground">Needs Configuration</h3>
          {unauthenticated.map(provider => (
            <div className="rounded-xl border p-6" key={provider.slug}>
              <div className="mb-4">
                <h4 className="font-medium">{provider.name}</h4>
                <p className="text-sm text-muted-foreground">Enter your API key to connect</p>
              </div>
              <ApiKeyForm
                name={provider.name}
                onValidated={() => setValidatedSlugs(prev => new Set([...prev, provider.slug]))}
                slug={provider.slug}
              />
            </div>
          ))}
        </div>
      )}

      {authenticated.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-muted-foreground">Authenticated</h3>
          {authenticated.map(provider => (
            <div className="flex items-center gap-3 rounded-lg border border-green-500/20 bg-green-500/5 px-4 py-3" key={provider.slug}>
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-green-500/20">
                <svg className="h-4 w-4 text-green-500" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24"><path d="M5 13l4 4L19 7" /></svg>
              </div>
              <div className="flex-1">
                <div className="text-sm font-medium">{provider.name}</div>
                <div className="text-xs text-green-600">Connected</div>
              </div>
              <Badge className="text-green-600 border-green-500/30" variant="outline">Verified</Badge>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
