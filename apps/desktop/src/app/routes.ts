export const SESSION_ROUTE_PREFIX = '/'
export const NEW_CHAT_ROUTE = '/'
export const SETTINGS_ROUTE = '/settings'
export const COMMAND_CENTER_ROUTE = '/command-center'
export const SKILLS_ROUTE = '/skills'
export const MESSAGING_ROUTE = '/messaging'
export const ARTIFACTS_ROUTE = '/artifacts'
export const CRON_ROUTE = '/cron'
export const PROFILES_ROUTE = '/profiles'
export const AGENTS_ROUTE = '/agents'
export const AGENT_HUB_ROUTE = '/agent-hub'
export const PROVIDERS_ROUTE = '/providers'
export const HOME_ROUTE = '/home'
export const PROJECTS_ROUTE = '/projects'
export const MODELS_ROUTE = '/models'
export const MEMORY_ROUTE = '/memory'
export const KNOWLEDGE_ROUTE = '/knowledge'
export const FILES_ROUTE = '/files'
export const BROWSER_ROUTE = '/browser'
export const AUTOMATION_ROUTE = '/automation'
export const COMPUTER_USE_ROUTE = '/computer'
export const EXTENSIONS_ROUTE = '/extensions'
export const EXTENSIONS_CENTER_ROUTE = '/extensions-center'
export const SERVICES_ROUTE = '/services'
export const COMMUNICATIONS_ROUTE = '/communications'
export const TASKS_ROUTE = '/tasks'
export const HISTORY_ROUTE = '/history'
export const LOGS_ROUTE = '/logs'
export const HELP_ROUTE = '/help'
export const UPDATES_ROUTE = '/updates'
export const SETTINGS_DEVELOPER_ROUTE = '/settings/developer'
export const SETTINGS_ADVANCED_ROUTE = '/settings/advanced'
export const MARKETPLACE_ROUTE = '/marketplace'
export const MCP_MANAGER_ROUTE = '/mcp-manager'
export const EXTENSION_SDK_ROUTE = '/extension-sdk'
export const DEVELOPER_TOOLS_ROUTE = '/developer-tools'
export const UPDATES_MANAGER_ROUTE = '/updates-manager'
export const SYNC_DASHBOARD_ROUTE = '/sync'
export const DEVICES_ROUTE = '/devices'
export const REMOTE_INSTANCES_ROUTE = '/remote-instances'
export const CONNECTION_WIZARD_ROUTE = '/connection-wizard'
export const CONFLICT_RESOLUTION_ROUTE = '/conflict-resolution'
export const SYNC_HISTORY_ROUTE = '/sync-history'
export const REMOTE_AGENT_DASHBOARD_ROUTE = '/remote-agent-dashboard'
export const SECURITY_CENTER_ROUTE = '/security'
export const MULTIMODAL_ROUTE = '/settings/multimodal'
export const TASK_ORCHESTRATOR_ROUTE = '/task-orchestrator'
export const SWARM_CENTER_ROUTE = '/swarm'
export const AUTOMATION_CENTER_ROUTE = '/automation-center'
export const VOICE_ASSISTANT_ROUTE = '/voice-assistant'
export const SCREEN_UNDERSTANDING_ROUTE = '/screen-understanding'
export const FILE_UNDERSTANDING_ROUTE = '/file-understanding'
export const ACCESSIBILITY_ROUTE = '/settings/accessibility'
export const PRIVACY_ROUTE = '/privacy'
export const RESOURCE_MANAGER_ROUTE = '/resource-manager'
export const DIAGNOSTICS_ROUTE = '/diagnostics'
export const SERVICE_MANAGER_ROUTE = '/service-manager'
export const SANDBOX_ROUTE = '/sandbox'
export const WORKSPACE_MANAGER_ROUTE = '/workspace-manager'
export const AI_ACTIONS_ROUTE = '/ai-actions'
export const DASHBOARD_ROUTE = '/dashboard'
export const JARVIS_MODE_ROUTE = '/jarvis'
export const AGENT_NETWORK_ROUTE = '/agent-network'
export const AGENT_MARKETPLACE_ROUTE = '/agent-marketplace'

export type AppView =
  | 'agents'
  | 'agent-hub'
  | 'artifacts'
  | 'chat'
  | 'command-center'
  | 'communications'
  | 'computer'
  | 'cron'
  | 'messaging'
  | 'profiles'
  | 'providers'
  | 'settings'
  | 'skills'
  | 'home'
  | 'projects'
  | 'models'
  | 'memory'
  | 'knowledge'
  | 'files'
  | 'browser'
  | 'automation'
  | 'extensions'
  | 'extensions-center'
  | 'services'
  | 'tasks'
  | 'history'
  | 'logs'
  | 'help'
  | 'updates'
  | 'settings-developer'
  | 'settings-advanced'
  | 'settings-multimodal'
  | 'marketplace'
  | 'mcp-manager'
  | 'extension-sdk'
  | 'developer-tools'
  | 'updates-manager'
  | 'sync-dashboard'
  | 'devices'
  | 'remote-instances'
  | 'connection-wizard'
  | 'conflict-resolution'
  | 'sync-history'
  | 'remote-agent-dashboard'
  | 'security-center'
  | 'task-orchestrator'
  | 'swarm-center'
  | 'agent-network'
  | 'agent-marketplace'
  | 'automation-center'
  | 'voice-assistant'
  | 'screen-understanding'
  | 'file-understanding'
  | 'accessibility'
  | 'privacy'
  | 'resource-manager'
  | 'diagnostics'
  | 'service-manager'
  | 'sandbox'
  | 'workspace-manager'
  | 'ai-actions'
  | 'dashboard'
  | 'jarvis-mode'

export type AppRouteId =
  | 'agents'
  | 'agent-hub'
  | 'artifacts'
  | 'command-center'
  | 'communications'
  | 'computer-use'
  | 'cron'
  | 'messaging'
  | 'new'
  | 'profiles'
  | 'providers'
  | 'settings'
  | 'skills'
  | 'home'
  | 'projects'
  | 'models'
  | 'memory'
  | 'knowledge'
  | 'files'
  | 'browser'
  | 'automation'
  | 'extensions'
  | 'extensions-center'
  | 'services'
  | 'tasks'
  | 'history'
  | 'logs'
  | 'help'
  | 'updates'
  | 'settings-developer'
  | 'settings-advanced'
  | 'settings-multimodal'
  | 'marketplace'
  | 'mcp-manager'
  | 'extension-sdk'
  | 'developer-tools'
  | 'updates-manager'
  | 'sync-dashboard'
  | 'devices'
  | 'remote-instances'
  | 'connection-wizard'
  | 'conflict-resolution'
  | 'sync-history'
  | 'remote-agent-dashboard'
  | 'security-center'
  | 'task-orchestrator'
  | 'swarm-center'
  | 'agent-network'
  | 'agent-marketplace'
  | 'automation-center'
  | 'voice-assistant'
  | 'screen-understanding'
  | 'file-understanding'
  | 'accessibility'
  | 'privacy'
  | 'resource-manager'
  | 'diagnostics'
  | 'service-manager'
  | 'sandbox'
  | 'workspace-manager'
  | 'ai-actions'
  | 'dashboard'
  | 'jarvis-mode'

export interface AppRoute {
  id: AppRouteId
  path: string
  view: AppView
}

export const APP_ROUTES = [
  { id: 'new', path: NEW_CHAT_ROUTE, view: 'chat' },
  { id: 'home', path: HOME_ROUTE, view: 'home' },
  { id: 'settings', path: SETTINGS_ROUTE, view: 'settings' },
  { id: 'settings-developer', path: SETTINGS_DEVELOPER_ROUTE, view: 'settings-developer' },
  { id: 'settings-advanced', path: SETTINGS_ADVANCED_ROUTE, view: 'settings-advanced' },
  { id: 'command-center', path: COMMAND_CENTER_ROUTE, view: 'command-center' },
  { id: 'skills', path: SKILLS_ROUTE, view: 'skills' },
  { id: 'messaging', path: MESSAGING_ROUTE, view: 'messaging' },
  { id: 'communications', path: COMMUNICATIONS_ROUTE, view: 'communications' },
  { id: 'artifacts', path: ARTIFACTS_ROUTE, view: 'artifacts' },
  { id: 'cron', path: CRON_ROUTE, view: 'cron' },
  { id: 'computer-use', path: COMPUTER_USE_ROUTE, view: 'computer' },
  { id: 'profiles', path: PROFILES_ROUTE, view: 'profiles' },
  { id: 'providers', path: PROVIDERS_ROUTE, view: 'providers' },
  { id: 'agents', path: AGENTS_ROUTE, view: 'agents' },
  { id: 'agent-hub', path: AGENT_HUB_ROUTE, view: 'agent-hub' },
  { id: 'projects', path: PROJECTS_ROUTE, view: 'projects' },
  { id: 'models', path: MODELS_ROUTE, view: 'models' },
  { id: 'memory', path: MEMORY_ROUTE, view: 'memory' },
  { id: 'knowledge', path: KNOWLEDGE_ROUTE, view: 'knowledge' },
  { id: 'files', path: FILES_ROUTE, view: 'files' },
  { id: 'browser', path: BROWSER_ROUTE, view: 'browser' },
  { id: 'automation', path: AUTOMATION_ROUTE, view: 'automation' },
  { id: 'extensions', path: EXTENSIONS_ROUTE, view: 'extensions' },
  { id: 'extensions-center', path: EXTENSIONS_CENTER_ROUTE, view: 'extensions-center' },
  { id: 'services', path: SERVICES_ROUTE, view: 'services' },
  { id: 'tasks', path: TASKS_ROUTE, view: 'tasks' },
  { id: 'history', path: HISTORY_ROUTE, view: 'history' },
  { id: 'logs', path: LOGS_ROUTE, view: 'logs' },
  { id: 'help', path: HELP_ROUTE, view: 'help' },
  { id: 'updates', path: UPDATES_ROUTE, view: 'updates' },
  { id: 'marketplace', path: MARKETPLACE_ROUTE, view: 'marketplace' },
  { id: 'mcp-manager', path: MCP_MANAGER_ROUTE, view: 'mcp-manager' },
  { id: 'extension-sdk', path: EXTENSION_SDK_ROUTE, view: 'extension-sdk' },
  { id: 'developer-tools', path: DEVELOPER_TOOLS_ROUTE, view: 'developer-tools' },
  { id: 'updates-manager', path: UPDATES_MANAGER_ROUTE, view: 'updates-manager' },
  { id: 'sync-dashboard', path: SYNC_DASHBOARD_ROUTE, view: 'sync-dashboard' },
  { id: 'devices', path: DEVICES_ROUTE, view: 'devices' },
  { id: 'remote-instances', path: REMOTE_INSTANCES_ROUTE, view: 'remote-instances' },
  { id: 'connection-wizard', path: CONNECTION_WIZARD_ROUTE, view: 'connection-wizard' },
  { id: 'conflict-resolution', path: CONFLICT_RESOLUTION_ROUTE, view: 'conflict-resolution' },
  { id: 'sync-history', path: SYNC_HISTORY_ROUTE, view: 'sync-history' },
  { id: 'remote-agent-dashboard', path: REMOTE_AGENT_DASHBOARD_ROUTE, view: 'remote-agent-dashboard' },
  { id: 'settings-multimodal', path: MULTIMODAL_ROUTE, view: 'settings-multimodal' },
  { id: 'security-center', path: SECURITY_CENTER_ROUTE, view: 'security-center' },
  { id: 'task-orchestrator', path: TASK_ORCHESTRATOR_ROUTE, view: 'task-orchestrator' },
  { id: 'swarm-center', path: SWARM_CENTER_ROUTE, view: 'swarm-center' },
  { id: 'agent-network', path: AGENT_NETWORK_ROUTE, view: 'agent-network' },
  { id: 'agent-marketplace', path: AGENT_MARKETPLACE_ROUTE, view: 'agent-marketplace' },
  { id: 'automation-center', path: AUTOMATION_CENTER_ROUTE, view: 'automation-center' },
  { id: 'voice-assistant', path: VOICE_ASSISTANT_ROUTE, view: 'voice-assistant' },
  { id: 'screen-understanding', path: SCREEN_UNDERSTANDING_ROUTE, view: 'screen-understanding' },
  { id: 'file-understanding', path: FILE_UNDERSTANDING_ROUTE, view: 'file-understanding' },
  { id: 'accessibility', path: ACCESSIBILITY_ROUTE, view: 'accessibility' },
  { id: 'privacy', path: PRIVACY_ROUTE, view: 'privacy' },
  { id: 'resource-manager', path: RESOURCE_MANAGER_ROUTE, view: 'resource-manager' },
  { id: 'diagnostics', path: DIAGNOSTICS_ROUTE, view: 'diagnostics' },
  { id: 'service-manager', path: SERVICE_MANAGER_ROUTE, view: 'service-manager' },
  { id: 'sandbox', path: SANDBOX_ROUTE, view: 'sandbox' },
  { id: 'workspace-manager', path: WORKSPACE_MANAGER_ROUTE, view: 'workspace-manager' },
  { id: 'ai-actions', path: AI_ACTIONS_ROUTE, view: 'ai-actions' },
  { id: 'dashboard', path: DASHBOARD_ROUTE, view: 'dashboard' },
  { id: 'jarvis-mode', path: JARVIS_MODE_ROUTE, view: 'jarvis-mode' }
] as const satisfies readonly AppRoute[]

const APP_VIEW_BY_PATH = new Map<string, AppView>(APP_ROUTES.map(route => [route.path, route.view]))
const RESERVED_PATHS: ReadonlySet<string> = new Set(APP_ROUTES.map(route => route.path))

// Views that render as a full-screen modal card (OverlayView) over the shell.
// While one is open the app's titlebar control clusters must hide so they don't
// bleed over the overlay (they sit at a higher z-index than the overlay card).
export const OVERLAY_VIEWS: ReadonlySet<AppView> = new Set(['agents', 'command-center', 'cron', 'profiles', 'settings'])

export function isOverlayView(view: AppView): boolean {
  return OVERLAY_VIEWS.has(view)
}

export function isNewChatRoute(pathname: string): boolean {
  return pathname === NEW_CHAT_ROUTE
}

export function routeSessionId(pathname: string): string | null {
  if (!pathname.startsWith(SESSION_ROUTE_PREFIX) || RESERVED_PATHS.has(pathname)) {
    return null
  }

  const id = pathname.slice(SESSION_ROUTE_PREFIX.length)

  return id && !id.includes('/') ? decodeURIComponent(id) : null
}

export function sessionRoute(sessionId: string): string {
  return `${SESSION_ROUTE_PREFIX}${encodeURIComponent(sessionId)}`
}

export function appViewForPath(pathname: string): AppView {
  if (isNewChatRoute(pathname) || routeSessionId(pathname)) {
    return 'chat'
  }

  return APP_VIEW_BY_PATH.get(pathname) ?? 'chat'
}
