import { useEffect, useState } from 'react'
import { useStore } from '@nanostores/react'
import {
  $route,
  $connectorDefinitions,
  $connectorInstances,
  loadConnectorDefinitions,
  loadConnectorInstances,
  installConnector,
  removeConnector,
  toggleConnector,
} from '../store'
import { Button } from '../components/button'
import { ArrowLeft, Plug, PlugZap, Trash2, Loader } from 'lucide-react'

export default function Connectors() {
  const definitions = useStore($connectorDefinitions)
  const instances = useStore($connectorInstances)
  const [loading, setLoading] = useState(true)
  const [showInstall, setShowInstall] = useState<string | null>(null)
  const [name, setName] = useState('')

  useEffect(() => {
    async function load() {
      await Promise.all([loadConnectorDefinitions(), loadConnectorInstances()])
      setLoading(false)
    }
    void load()
  }, [])

  const enabledCount = instances.filter(i => i.enabled).length
  const connectedCount = instances.filter(i => i.connected).length

  async function handleInstall(defId: string) {
    try {
      await installConnector(defId, name || defId, {})
      setName('')
      setShowInstall(null)
    } catch (e) {
      console.error(e)
    }
  }

  async function handleToggle(id: string, enabled: boolean) {
    try {
      await toggleConnector(id, enabled)
    } catch (e) {
      console.error(e)
    }
  }

  async function handleRemove(id: string) {
    try {
      await removeConnector(id)
    } catch (e) {
      console.error(e)
    }
  }

  return (
    <div className="flex h-full flex-col gap-6 px-12 py-10">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => $route.set('complete')}
            className="flex size-8 items-center justify-center rounded-lg border border-border/40 text-muted-foreground hover:bg-muted/40 hover:text-foreground"
          >
            <ArrowLeft size={18} />
          </button>
          <div>
            <h1 className="text-xl font-bold tracking-tight">Connectors</h1>
            <p className="text-sm text-muted-foreground">
              Manage service integrations for messaging, email, source control, and more
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <span>{instances.length} installed</span>
          <span className="text-emerald-500">{connectedCount} connected</span>
          <span className="text-amber-500">{enabledCount - connectedCount} enabled</span>
        </div>
      </div>

      {loading ? (
        <div className="flex flex-1 items-center justify-center">
          <Loader size={24} className="animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="flex flex-1 flex-col gap-4 overflow-y-auto">
          {instances.map((inst) => {
            const def = definitions.find(d => d.id === inst.definition_id)
            return (
              <div key={inst.id} className="flex items-center gap-4 rounded-lg border border-border/40 bg-card/30 px-4 py-3">
                <div className={`flex size-8 shrink-0 items-center justify-center rounded-lg ${
                  inst.connected ? 'bg-emerald-500/15 text-emerald-500' :
                  inst.enabled ? 'bg-amber-500/15 text-amber-500' :
                  'bg-muted/40 text-muted-foreground'
                }`}>
                  {inst.connected ? <PlugZap size={16} /> : <Plug size={16} />}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{inst.name}</span>
                    <span className="rounded bg-muted/40 px-1.5 py-0.5 text-xs text-muted-foreground">
                      {def?.name ?? inst.definition_id}
                    </span>
                  </div>
                  <p className="truncate text-xs text-muted-foreground">
                    {def?.description ?? ''}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs ${
                    inst.connected ? 'bg-emerald-500/10 text-emerald-500' :
                    inst.enabled ? 'bg-amber-500/10 text-amber-500' :
                    'bg-muted/30 text-muted-foreground'
                  }`}>
                    {inst.connected ? 'Connected' : inst.enabled ? 'Enabled' : 'Disabled'}
                  </span>
                  {inst.health.latency_ms > 0 && (
                    <span className="text-xs text-muted-foreground">
                      {inst.health.latency_ms}ms
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleToggle(inst.id, !inst.enabled)}
                    className="text-xs"
                  >
                    {inst.enabled ? 'Disable' : 'Enable'}
                  </Button>
                  <button
                    onClick={() => handleRemove(inst.id)}
                    className="flex size-7 items-center justify-center rounded-md text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            )
          })}

          <div className="mt-2">
            <h3 className="mb-2 text-sm font-medium text-muted-foreground">
              Available Connectors
            </h3>
            <div className="grid grid-cols-2 gap-2">
              {definitions.filter(d => !instances.some(i => i.definition_id === d.id)).map((def) => (
                <div key={def.id} className="rounded-lg border border-border/30 bg-card/20 px-3 py-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{def.name}</span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => { setShowInstall(def.id); setName(def.name); }}
                      className="text-xs"
                    >
                      Install
                    </Button>
                  </div>
                  <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">{def.description}</p>
                  <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                    <span className="rounded bg-muted/30 px-1 py-0.5">{def.auth_type}</span>
                    <span>{def.category}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {showInstall && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-96 rounded-xl border border-border/60 bg-card p-6 shadow-xl">
            <h2 className="mb-1 text-lg font-semibold">Install Connector</h2>
            <p className="mb-4 text-sm text-muted-foreground">
              {definitions.find(d => d.id === showInstall)?.name}
            </p>
            <label className="mb-1 block text-sm font-medium">Instance name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="mb-4 w-full rounded-lg border border-border/40 bg-background px-3 py-2 text-sm"
              placeholder="My connector"
            />
            <div className="flex justify-end gap-2">
              <Button variant="outline" size="sm" onClick={() => setShowInstall(null)}>Cancel</Button>
              <Button size="sm" onClick={() => handleInstall(showInstall)}>Install</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
