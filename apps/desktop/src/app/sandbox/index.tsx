import { useStore } from '@nanostores/react'

import { PageDescription, PageHeader, PageShell, PageTitle } from '@/app/page-shell'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import {
  AlertTriangle,
  Eye,
  Globe,
  Monitor as HardDrive,
  Lock,
  Mic as Microphone,
  Monitor,
  Terminal,
  Wrench,
  Zap
} from '@/lib/icons'
import { cn } from '@/lib/utils'
import { notify } from '@/store/notifications'
import {
  $sandbox,
  setDefaultPolicy,
  setGlobalFileSystemRestriction,
  setGlobalNetworkBlock,
  setIsolationLevel,
  setSandboxTab,
  updatePermission,
  updatePlugin
} from '@/store/sandbox'
import type { PermissionRule, SandboxedPlugin, SandboxResource } from '@/store/sandbox'

const RESOURCE_ICONS: Record<SandboxResource, any> = {
  filesystem: HardDrive,
  network: Globe,
  process: Terminal,
  clipboard: Eye,
  notifications: AlertTriangle,
  camera: Monitor,
  microphone: Microphone,
  screen: Monitor,
  usb: Zap,
  bluetooth: Wrench
}

const RESOURCE_LABELS: Record<SandboxResource, string> = {
  filesystem: 'File System',
  network: 'Network',
  process: 'Process Execution',
  clipboard: 'Clipboard',
  notifications: 'Notifications',
  camera: 'Camera',
  microphone: 'Microphone',
  screen: 'Screen Capture',
  usb: 'USB Devices',
  bluetooth: 'Bluetooth'
}

export function SandboxView() {
  const state = useStore($sandbox)

  const tabs = [
    { id: 'plugins' as const, label: 'Plugins', icon: Lock },
    { id: 'permissions' as const, label: 'Permissions', icon: Lock },
    { id: 'events' as const, label: 'Events', icon: AlertTriangle },
    { id: 'settings' as const, label: 'Settings', icon: Wrench }
  ]

  return (
    <PageShell
      header={
        <PageHeader className="w-full">
          <div>
            <PageTitle>Secure Sandbox</PageTitle>
            <PageDescription>Plugin isolation, permissions, and security policies</PageDescription>
          </div>
        </PageHeader>
      }
    >
      <div className="flex h-full flex-col gap-0">
        <div className="flex shrink-0 items-center gap-1 border-b border-(--ui-stroke-tertiary)">
          {tabs.map(tab => {
            const Icon = tab.icon

            return (
              <button
                className={cn(
                  'flex items-center gap-1.5 border-b-2 px-4 py-2 text-xs font-medium transition-colors',
                  state.selectedTab === tab.id ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'
                )}
                key={tab.id}
                onClick={() => setSandboxTab(tab.id)}
                type="button"
              >
                <Icon className="size-3.5" />
                {tab.label}
              </button>
            )
          })}
        </div>

        {state.selectedTab === 'plugins' && (
          <div className="flex-1 space-y-3 overflow-y-auto p-4">
            {state.plugins.map(plugin => (
              <SandboxPluginCard key={plugin.id} plugin={plugin} />
            ))}
          </div>
        )}

        {state.selectedTab === 'permissions' && (
          <div className="flex-1 overflow-y-auto p-4">
            <div className="space-y-4">
              {state.plugins.map(plugin => (
                <div className="rounded-xl border border-(--ui-stroke-tertiary) p-4" key={plugin.id}>
                  <h4 className="mb-3 text-xs font-semibold text-foreground">{plugin.name} — Permissions</h4>
                  <div className="space-y-2">
                    {plugin.permissions.map(perm => (
                      <PermissionRow key={perm.id} permission={perm} />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {state.selectedTab === 'events' && (
          <div className="flex-1 overflow-y-auto p-4">
            {state.events.length === 0 ? (
              <p className="py-8 text-center text-xs text-muted-foreground">No sandbox events recorded</p>
            ) : state.events.slice(-50).reverse().map(event => (
              <div className="flex items-center gap-3 border-b border-(--ui-stroke-tertiary)/50 py-2 text-xs" key={event.id}>
                <AlertTriangle className={cn('size-3.5 shrink-0', event.blocked ? 'text-red-500' : 'text-amber-500')} />
                <div className="min-w-0 flex-1">
                  <div className="font-medium text-foreground">{event.detail}</div>
                  <div className="text-muted-foreground">{event.pluginId} — {event.type}</div>
                </div>
                <span className="shrink-0 text-muted-foreground/60">{new Date(event.timestamp).toLocaleTimeString()}</span>
              </div>
            ))}
          </div>
        )}

        {state.selectedTab === 'settings' && (
          <div className="flex-1 space-y-4 overflow-y-auto p-4">
            <div className="rounded-xl border border-(--ui-stroke-tertiary) p-4">
              <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Global Policies</h4>
              <div className="space-y-3">
                <label className="flex items-center justify-between gap-2 text-xs">
                  <div>
                    <div className="font-medium text-foreground">Default Permission Policy</div>
                    <div className="text-muted-foreground">How to handle permissions by default</div>
                  </div>
                  <select
                    className="rounded-md border border-(--ui-stroke-tertiary) bg-transparent px-2 py-1 text-xs text-foreground"
                    onChange={e => setDefaultPolicy(e.target.value as any)}
                    value={state.defaultPolicy}
                  >
                    <option value="allow">Allow</option>
                    <option value="deny">Deny</option>
                    <option value="prompt">Prompt</option>
                  </select>
                </label>
                <label className="flex items-center justify-between gap-2 text-xs">
                  <div>
                    <div className="font-medium text-foreground">Isolation Level</div>
                    <div className="text-muted-foreground">Sandbox strictness for plugins</div>
                  </div>
                  <select
                    className="rounded-md border border-(--ui-stroke-tertiary) bg-transparent px-2 py-1 text-xs text-foreground"
                    onChange={e => setIsolationLevel(e.target.value as any)}
                    value={state.isolationLevel}
                  >
                    <option value="strict">Strict</option>
                    <option value="moderate">Moderate</option>
                    <option value="permissive">Permissive</option>
                  </select>
                </label>
                <label className="flex items-center justify-between gap-2 text-xs">
                  <div>
                    <div className="font-medium text-foreground">Global Network Block</div>
                    <div className="text-muted-foreground">Block all network access for all plugins</div>
                  </div>
                  <Switch checked={state.globalNetworkBlock} onCheckedChange={setGlobalNetworkBlock} />
                </label>
                <label className="flex items-center justify-between gap-2 text-xs">
                  <div>
                    <div className="font-medium text-foreground">File System Restriction</div>
                    <div className="text-muted-foreground">Restrict file system access across all plugins</div>
                  </div>
                  <Switch checked={state.globalFileSystemRestriction} onCheckedChange={setGlobalFileSystemRestriction} />
                </label>
              </div>
            </div>
          </div>
        )}
      </div>
    </PageShell>
  )
}

function SandboxPluginCard({ plugin }: { plugin: SandboxedPlugin }) {
  return (
    <div className="rounded-xl border border-(--ui-stroke-tertiary) p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-foreground">{plugin.name}</span>
            <Badge className={cn(
              plugin.status === 'active' ? 'bg-emerald-500/10 text-emerald-500' :
              plugin.status === 'blocked' ? 'bg-red-500/10 text-red-500' :
              'bg-amber-500/10 text-amber-500'
            )} variant="secondary">{plugin.status}</Badge>
          </div>
          <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
            <span>v{plugin.version}</span>
            <span>Isolation: {plugin.isolation}</span>
            <span>Memory: {plugin.memoryLimit} MB</span>
            <span>CPU: {plugin.cpuLimit}%</span>
          </div>
        </div>
        <Button
          className={plugin.status === 'blocked' ? 'text-emerald-500' : 'text-muted-foreground'}
          onClick={() => {
            const next = plugin.status === 'active' ? 'blocked' : 'active'
            updatePlugin(plugin.id, { status: next })
            notify({ kind: 'info', title: plugin.name, message: next === 'active' ? 'Plugin unblocked' : 'Plugin blocked' })
          }}
          size="icon-xs"
          variant="ghost"
        >
          <Lock className="size-3" />
        </Button>
      </div>
      {plugin.networkAccess !== 'none' && (
        <div className="mt-2 flex flex-wrap gap-1">
          {plugin.allowedDomains.map(domain => (
            <Badge className="bg-(--ui-bg-quinary) text-muted-foreground" key={domain} variant="secondary">{domain}</Badge>
          ))}
        </div>
      )}
    </div>
  )
}

function PermissionRow({ permission }: { permission: PermissionRule }) {
  const Icon = RESOURCE_ICONS[permission.resource]

  return (
    <div className="flex items-center justify-between gap-2 rounded-md px-2 py-1 text-xs hover:bg-accent/60">
      <div className="flex items-center gap-2">
        <Icon className="size-3 text-muted-foreground" />
        <span className="text-foreground">{RESOURCE_LABELS[permission.resource]}</span>
      </div>
      <div className="flex items-center gap-2">
        <label className="flex items-center gap-1 text-muted-foreground">
          <Switch
            checked={permission.allowed}
            onCheckedChange={v => updatePermission(permission.id, { allowed: v })}
          />
          {permission.allowed ? 'Allow' : 'Deny'}
        </label>
        <label className="flex items-center gap-1 text-muted-foreground">
          <Switch
            checked={permission.promptUser}
            onCheckedChange={v => updatePermission(permission.id, { promptUser: v })}
          />
          Prompt
        </label>
      </div>
    </div>
  )
}
