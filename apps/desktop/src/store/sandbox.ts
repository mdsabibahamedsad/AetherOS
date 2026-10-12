import { atom } from 'nanostores'

export type SandboxResource = 'filesystem' | 'network' | 'process' | 'clipboard' | 'notifications' | 'camera' | 'microphone' | 'screen' | 'usb' | 'bluetooth'

export interface PermissionRule {
  id: string
  pluginId: string
  resource: SandboxResource
  allowed: boolean
  promptUser: boolean
  maxUsage?: number
  expiry?: number
}

export interface SandboxedPlugin {
  id: string
  name: string
  version: string
  permissions: PermissionRule[]
  isolation: 'process' | 'worker' | 'iframe'
  memoryLimit: number
  networkAccess: 'none' | 'local' | 'selected' | 'all'
  allowedDomains: string[]
  status: 'active' | 'blocked' | 'suspended'
  cpuLimit: number
}

export interface SandboxEvent {
  id: string
  pluginId: string
  timestamp: number
  type: 'access_denied' | 'access_granted' | 'resource_exceeded' | 'isolation_breach' | 'policy_violation'
  detail: string
  blocked: boolean
}

export interface SandboxState {
  plugins: SandboxedPlugin[]
  events: SandboxEvent[]
  defaultPolicy: 'allow' | 'deny' | 'prompt'
  isolationLevel: 'strict' | 'moderate' | 'permissive'
  globalNetworkBlock: boolean
  globalFileSystemRestriction: boolean
  selectedTab: 'plugins' | 'permissions' | 'events' | 'settings'
}

const DEFAULT_PLUGINS: SandboxedPlugin[] = [
  {
    id: 'code-analyzer', name: 'Code Analyzer', version: '2.1.0',
    permissions: [
      { id: 'ca-fs', pluginId: 'code-analyzer', resource: 'filesystem', allowed: true, promptUser: false },
      { id: 'ca-net', pluginId: 'code-analyzer', resource: 'network', allowed: false, promptUser: true }
    ],
    isolation: 'worker', memoryLimit: 256, networkAccess: 'none', allowedDomains: [], status: 'active', cpuLimit: 50
  },
  {
    id: 'search-assistant', name: 'Search Assistant', version: '1.3.2',
    permissions: [
      { id: 'sa-fs', pluginId: 'search-assistant', resource: 'filesystem', allowed: true, promptUser: true },
      { id: 'sa-net', pluginId: 'search-assistant', resource: 'network', allowed: true, promptUser: false }
    ],
    isolation: 'worker', memoryLimit: 128, networkAccess: 'selected', allowedDomains: ['api.search.com'], status: 'active', cpuLimit: 30
  },
  {
    id: 'task-automation', name: 'Task Automation', version: '3.0.1',
    permissions: [
      { id: 'ta-fs', pluginId: 'task-automation', resource: 'filesystem', allowed: true, promptUser: false },
      { id: 'ta-net', pluginId: 'task-automation', resource: 'network', allowed: true, promptUser: false },
      { id: 'ta-proc', pluginId: 'task-automation', resource: 'process', allowed: false, promptUser: true }
    ],
    isolation: 'process', memoryLimit: 512, networkAccess: 'local', allowedDomains: [], status: 'active', cpuLimit: 60
  },
  {
    id: 'screen-capture', name: 'Screen Capture', version: '1.0.0',
    permissions: [
      { id: 'sc-screen', pluginId: 'screen-capture', resource: 'screen', allowed: true, promptUser: true },
      { id: 'sc-fs', pluginId: 'screen-capture', resource: 'filesystem', allowed: true, promptUser: true }
    ],
    isolation: 'worker', memoryLimit: 384, networkAccess: 'none', allowedDomains: [], status: 'active', cpuLimit: 40
  }
]

export const $sandbox = atom<SandboxState>({
  plugins: DEFAULT_PLUGINS,
  events: [],
  defaultPolicy: 'prompt',
  isolationLevel: 'moderate',
  globalNetworkBlock: false,
  globalFileSystemRestriction: false,
  selectedTab: 'plugins'
})

const patch = (u: Partial<SandboxState>) =>
  $sandbox.set({ ...$sandbox.get(), ...u })

export function setSandboxTab(tab: SandboxState['selectedTab']) { patch({ selectedTab: tab }) }

export function setDefaultPolicy(p: SandboxState['defaultPolicy']) { patch({ defaultPolicy: p }) }

export function setIsolationLevel(l: SandboxState['isolationLevel']) { patch({ isolationLevel: l }) }

export function setGlobalNetworkBlock(v: boolean) { patch({ globalNetworkBlock: v }) }

export function setGlobalFileSystemRestriction(v: boolean) { patch({ globalFileSystemRestriction: v }) }

export function addSandboxEvent(event: SandboxEvent) {
  patch({ events: [...$sandbox.get().events.slice(-99), event] })
}

export function updatePlugin(id: string, update: Partial<SandboxedPlugin>) {
  const plugins = $sandbox.get().plugins.map(p => p.id === id ? { ...p, ...update } : p)
  patch({ plugins })
}

export function updatePermission(id: string, update: Partial<PermissionRule>) {
  const plugins = $sandbox.get().plugins.map(p => ({
    ...p,
    permissions: p.permissions.map(r => r.id === id ? { ...r, ...update } : r)
  }))

  patch({ plugins })
}
