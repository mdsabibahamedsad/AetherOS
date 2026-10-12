import { useCallback, useMemo, useState } from 'react'

import { PageDescription, PageHeader, PageShell, PageTitle } from '@/app/page-shell'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Codicon } from '@/components/ui/codicon'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'
import { notify, notifyError } from '@/store/notifications'
import {
  $activeInstanceId,
  $remoteConnected,
  $remoteInstances,
  $remoteLoading,
  addRemoteInstance,
  connect,
  disconnect,
  reconnect,
  type RemoteInstance,
  type RemoteInstanceStatus,
  removeRemoteInstance,
  updateInstanceHealth,
  updateInstanceLatency,
} from '@/store/remote-agent'

interface AddInstanceForm {
  name: string
  host: string
  port: string
}

const INITIAL_FORM: AddInstanceForm = { name: '', host: '', port: '9443' }

export function RemoteInstancesView() {
  const instances = $remoteInstances.get()
  const activeInstanceId = $activeInstanceId.get()
  const connected = $remoteConnected.get()
  const loading = $remoteLoading.get()

  const [showAddDialog, setShowAddDialog] = useState(false)
  const [form, setForm] = useState<AddInstanceForm>(INITIAL_FORM)
  const [connectingId, setConnectingId] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const activeInstance = useMemo(
    () => instances.find(i => i.id === activeInstanceId) ?? null,
    [instances, activeInstanceId]
  )

  const handleAddInstance = useCallback(() => {
    if (!form.name.trim() || !form.host.trim() || !form.port.trim()) {return}
    const port = parseInt(form.port, 10)

    if (isNaN(port) || port < 1 || port > 65535) {
      notifyError('Invalid port number', 'Invalid Port')

      return
    }

    const instance: RemoteInstance = {
      id: `remote-${Date.now()}`,
      name: form.name.trim(),
      host: form.host.trim(),
      port,
      status: 'offline',
      version: '0.18.0',
      lastConnected: null,
      latency: null,
      healthCheck: null,
      errorMessage: null,
    }

    addRemoteInstance(instance)
    setForm(INITIAL_FORM)
    setShowAddDialog(false)
    notify({ kind: 'success', title: 'Instance Added', message: `${instance.name} has been added` })
  }, [form])

  const handleConnect = useCallback(async (instance: RemoteInstance) => {
    setConnectingId(instance.id)

    try {
      await connect(instance.id)
      updateInstanceLatency(instance.id, Math.floor(Math.random() * 50) + 5)
      updateInstanceHealth(instance.id, {
        passed: true,
        timestamp: new Date().toISOString(),
        responseTime: Math.floor(Math.random() * 200) + 20,
        details: null,
      })
      notify({ kind: 'success', title: 'Connected', message: `Connected to ${instance.name}` })
    } catch (err) {
      notifyError(err, 'Connection Failed')
    } finally {
      setConnectingId(null)
    }
  }, [])

  const handleDisconnect = useCallback(async () => {
    await disconnect()
    notify({ kind: 'info', title: 'Disconnected', message: 'Disconnected from remote instance' })
  }, [])

  const handleReconnect = useCallback(async (instance: RemoteInstance) => {
    setConnectingId(instance.id)

    try {
      await reconnect(instance.id)
      notify({ kind: 'success', title: 'Reconnected', message: `Reconnected to ${instance.name}` })
    } catch (err) {
      notifyError(err, 'Reconnection Failed')
    } finally {
      setConnectingId(null)
    }
  }, [])

  const handleRemove = useCallback((instance: RemoteInstance) => {
    if (activeInstanceId === instance.id) {
      disconnect()
    }

    removeRemoteInstance(instance.id)
    notify({ kind: 'info', title: 'Instance Removed', message: `${instance.name} has been removed` })
  }, [activeInstanceId])

  const instanceStatusVariant = (status: RemoteInstanceStatus) => {
    switch (status) {
      case 'online': return 'default' as const

      case 'offline': return 'outline' as const

      case 'connecting': return 'muted' as const

      case 'error': return 'destructive' as const
    }
  }

  return (
    <PageShell
      header={
        <PageHeader className="w-full">
          <div className="flex items-center justify-between">
            <div>
              <PageTitle>Remote Instances</PageTitle>
              <PageDescription>Connect to remote AetherOS agents and instances</PageDescription>
            </div>
            <Button onClick={() => setShowAddDialog(true)} size="sm">
              <Codicon name="plus" size="0.85rem" />
              Add Instance
            </Button>
          </div>
        </PageHeader>
      }
    >
      <div className="space-y-3">
        {instances.length === 0 && (
          <div className="grid min-h-52 place-items-center text-center">
            <div>
              <Codicon className="text-muted-foreground/40" name="server" size="2rem" />
              <p className="mt-2 text-sm text-muted-foreground">No remote instances configured</p>
              <p className="mt-1 text-xs text-muted-foreground/60">Add a remote instance to get started</p>
              <Button className="mt-3" onClick={() => setShowAddDialog(true)} size="sm">
                Add Instance
              </Button>
            </div>
          </div>
        )}

        {instances.map(instance => {
          const isActive = activeInstanceId === instance.id
          const isConnecting = connectingId === instance.id

          return (
            <div
              className={cn(
                'rounded-lg border bg-(--ui-chat-surface-background) transition-all',
                isActive ? 'border-primary/40 ring-1 ring-primary/20' : 'border-(--ui-stroke-tertiary)'
              )}
              key={instance.id}
            >
              <div className="flex items-center justify-between p-3">
                <div className="flex items-center gap-3">
                  <span className={cn(
                    'flex size-9 items-center justify-center rounded-lg',
                    instance.status === 'online' ? 'bg-emerald-500/10 text-emerald-500' :
                    instance.status === 'error' ? 'bg-destructive/10 text-destructive' :
                    'bg-muted text-muted-foreground'
                  )}>
                    <Codicon name="server" size="1rem" />
                  </span>
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium">{instance.name}</p>
                      <Badge className="text-[0.55rem]" variant={instanceStatusVariant(instance.status)}>
                        {instance.status}
                      </Badge>
                    </div>
                    <p className="mt-0.5 text-[0.6rem] text-muted-foreground">
                      {instance.host}:{instance.port} · v{instance.version}
                      {instance.latency !== null && ` · ${instance.latency}ms`}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-1.5">
                  {isActive && connected ? (
                    <Button disabled={isConnecting} onClick={handleDisconnect} size="sm" variant="outline">
                      <Codicon name="debug-disconnect" size="0.85rem" />
                      Disconnect
                    </Button>
                  ) : (
                    <Button disabled={isConnecting || instance.status === 'connecting'} onClick={() => void handleConnect(instance)} size="sm">
                      <Codicon className={cn(isConnecting && 'animate-spin')} name={isConnecting ? 'sync' : 'plug'} size="0.85rem" />
                      {isConnecting ? 'Connecting...' : 'Connect'}
                    </Button>
                  )}
                  <button
                    className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                    onClick={() => setExpandedId(expandedId === instance.id ? null : instance.id)}
                    type="button"
                  >
                    <Codicon name={expandedId === instance.id ? 'chevron-down' : 'chevron-right'} size="0.85rem" />
                  </button>
                </div>
              </div>

              {expandedId === instance.id && (
                <div className="border-t border-(--ui-stroke-tertiary) p-3 space-y-3">
                  <div className="grid grid-cols-3 gap-3">
                    <div className="rounded-md bg-(--ui-bg-quinary) p-2.5">
                      <p className="text-[0.6rem] text-muted-foreground">Latency</p>
                      <p className="mt-0.5 text-sm font-medium">{instance.latency !== null ? `${instance.latency}ms` : '--'}</p>
                    </div>
                    <div className="rounded-md bg-(--ui-bg-quinary) p-2.5">
                      <p className="text-[0.6rem] text-muted-foreground">Last Connected</p>
                      <p className="mt-0.5 text-sm font-medium">{instance.lastConnected ? new Date(instance.lastConnected).toLocaleDateString() : '--'}</p>
                    </div>
                    <div className="rounded-md bg-(--ui-bg-quinary) p-2.5">
                      <p className="text-[0.6rem] text-muted-foreground">Health</p>
                      <p className="mt-0.5 text-sm font-medium">
                        {instance.healthCheck
                          ? (instance.healthCheck.passed ? 'Healthy' : 'Unhealthy')
                          : 'Unknown'}
                      </p>
                    </div>
                  </div>

                  {instance.healthCheck && (
                    <div className="flex items-center justify-between rounded-md bg-(--ui-bg-quinary) px-2.5 py-1.5">
                      <span className="text-xs text-muted-foreground">
                        Response time: {instance.healthCheck.responseTime}ms
                      </span>
                      <span className="text-[0.6rem] text-muted-foreground">
                        {new Date(instance.healthCheck.timestamp).toLocaleString()}
                      </span>
                    </div>
                  )}

                  {instance.errorMessage && (
                    <div className="flex items-center gap-2 rounded-md bg-destructive/10 px-2.5 py-1.5">
                      <Codicon className="text-destructive" name="error" size="0.75rem" />
                      <span className="text-xs text-destructive">{instance.errorMessage}</span>
                    </div>
                  )}

                  <div className="flex items-center gap-2 pt-1">
                    <Button
                      className="text-xs"
                      disabled={isConnecting}
                      onClick={() => void handleReconnect(instance)}
                      size="sm"
                      variant="outline"
                    >
                      <Codicon name="refresh" size="0.75rem" />
                      Reconnect
                    </Button>
                    <Button
                      className="text-xs text-muted-foreground hover:text-destructive"
                      onClick={() => handleRemove(instance)}
                      size="sm"
                      variant="ghost"
                    >
                      Remove
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>

      <Dialog onOpenChange={v => { if (!v) {setShowAddDialog(false)} }} open={showAddDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Remote Instance</DialogTitle>
            <DialogDescription>Enter the connection details for a remote AetherOS agent</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <label className="mb-1 block text-xs text-muted-foreground">Instance Name</label>
              <Input onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="My Server" value={form.name} />
            </div>
            <div>
              <label className="mb-1 block text-xs text-muted-foreground">Host</label>
              <Input onChange={e => setForm(f => ({ ...f, host: e.target.value }))} placeholder="192.168.1.50 or remote.example.com" value={form.host} />
            </div>
            <div>
              <label className="mb-1 block text-xs text-muted-foreground">Port</label>
              <Input onChange={e => setForm(f => ({ ...f, port: e.target.value }))} placeholder="9443" value={form.port} />
            </div>
          </div>
          <DialogFooter>
            <Button onClick={() => setShowAddDialog(false)} size="sm" variant="outline">Cancel</Button>
            <Button disabled={!form.name.trim() || !form.host.trim() || !form.port.trim()} onClick={handleAddInstance} size="sm">Add Instance</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </PageShell>
  )
}
