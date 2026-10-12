import { useStore } from '@nanostores/react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { $providerManager, updateSettings } from '@/store/provider-manager'

export function ProviderSettings() {
  const settings = useStore($providerManager).settings
  const providers = useStore($providerManager).providers.filter(p => p.authenticated)

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="border-b px-6 py-4">
        <h2 className="text-lg font-semibold">Provider Settings</h2>
        <p className="text-sm text-muted-foreground">Global settings for AI provider connections</p>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-2xl space-y-8">
          <div className="rounded-xl border p-5">
            <h3 className="mb-4 text-sm font-medium text-muted-foreground uppercase tracking-wider">Connection</h3>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Timeout (ms)</Label>
                  <Input
                    className="font-mono text-sm"
                    onChange={e => updateSettings({ timeout: parseInt(e.target.value) || 30000 })}
                    type="number"
                    value={settings.timeout}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Max Retries</Label>
                  <Input
                    className="font-mono text-sm"
                    onChange={e => updateSettings({ retries: parseInt(e.target.value) || 3 })}
                    type="number"
                    value={settings.retries}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label>Max Concurrent Requests</Label>
                <Input
                  className="font-mono text-sm max-w-[200px]"
                  onChange={e => updateSettings({ maxConcurrency: parseInt(e.target.value) || 5 })}
                  type="number"
                  value={settings.maxConcurrency}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Fallback Provider</Label>
                  <Select onValueChange={v => updateSettings({ fallbackProvider: v || null })} value={settings.fallbackProvider ?? ''}>
                    <SelectTrigger><SelectValue placeholder="None" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">None</SelectItem>
                      {providers.map(p => <SelectItem key={p.slug} value={p.slug}>{p.name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Preferred Provider</Label>
                  <Select onValueChange={v => updateSettings({ preferredProvider: v || null })} value={settings.preferredProvider ?? ''}>
                    <SelectTrigger><SelectValue placeholder="Auto" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">Auto</SelectItem>
                      {providers.map(p => <SelectItem key={p.slug} value={p.slug}>{p.name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
          </div>

          <div className="rounded-xl border p-5">
            <h3 className="mb-4 text-sm font-medium text-muted-foreground uppercase tracking-wider">Features</h3>
            <div className="space-y-4">
              {[
                { id: 'streaming' as const, label: 'Streaming', description: 'Enable streaming responses' },
                { id: 'parallelRequests' as const, label: 'Parallel Requests', description: 'Allow concurrent requests to the same provider' },
                { id: 'caching' as const, label: 'Response Caching', description: 'Cache responses for identical requests' },
                { id: 'compression' as const, label: 'Compression', description: 'Compress request/response data' }
              ].map(feature => (
                <div className="flex items-center justify-between rounded-lg border p-4" key={feature.id}>
                  <div>
                    <Label className="text-base">{feature.label}</Label>
                    <p className="text-sm text-muted-foreground">{feature.description}</p>
                  </div>
                  <Switch
                    checked={settings[feature.id]}
                    onCheckedChange={v => updateSettings({ [feature.id]: v })}
                  />
                </div>
              ))}
            </div>
          </div>

          <div className="flex justify-end gap-3">
            <Button variant="outline">Reset to Defaults</Button>
            <Button>Save Settings</Button>
          </div>
        </div>
      </div>
    </div>
  )
}
