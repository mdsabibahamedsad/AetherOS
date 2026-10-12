import { atom } from 'nanostores'

export type NavSectionId =
  | 'home'
  | 'chat'
  | 'jarvis-mode'
  | 'projects'
  | 'agents'
  | 'models'
  | 'memory'
  | 'knowledge'
  | 'files'
  | 'browser'
  | 'automation'
  | 'tasks'
  | 'communications'
  | 'history'
  | 'task-orchestrator'
  | 'extensions'
  | 'mcp'
  | 'security'
  | 'services'
  | 'diagnostics'
  | 'settings'
  | 'help'
  | 'updates'
  // More section (progressive disclosure)
  | 'service-manager'
  | 'resource-manager'
  | 'sandbox'
  | 'workspace-manager'

export type NavGroupId = 'workspace' | 'ai' | 'work' | 'system' | 'more'

export interface NavSection {
  id: NavSectionId
  label: string
  icon: string
  route: string
  /** Progressive-disclosure group rendered as a sidebar section header. */
  group: NavGroupId
  badge?: number
  children?: NavSection[]
}

export const NAV_GROUP_META: readonly { id: NavGroupId; label: string }[] = [
  { id: 'workspace', label: 'Workspace' },
  { id: 'ai', label: 'AI' },
  { id: 'work', label: 'Work' },
  { id: 'system', label: 'System' },
  { id: 'more', label: 'More' },
]

export const NAV_SECTIONS: NavSection[] = [
  // Routes must resolve in APP_ROUTES (src/app/routes.ts). '/' is the chat
  // root (new session); anything else unregistered is swallowed by
  // routeSessionId() and opens a bogus session — never point nav there.
  { id: 'home', label: 'Home', icon: 'home', route: '/home', group: 'workspace' },
  { id: 'chat', label: 'Chat', icon: 'comment-discussion', route: '/', group: 'workspace' },
  { id: 'jarvis-mode', label: 'Jarvis', icon: 'hubot', route: '/jarvis', group: 'workspace' },
  { id: 'projects', label: 'Projects', icon: 'project', route: '/projects', group: 'workspace' },
  { id: 'agents', label: 'Agents', icon: 'robot', route: '/agents', group: 'ai' },
  { id: 'models', label: 'Models', icon: 'symbol-method', route: '/models', group: 'ai' },
  { id: 'memory', label: 'Memory', icon: 'database', route: '/memory', group: 'ai' },
  { id: 'knowledge', label: 'Knowledge', icon: 'book', route: '/knowledge', group: 'ai' },
  { id: 'files', label: 'Files', icon: 'file-directory', route: '/files', group: 'work' },
  { id: 'browser', label: 'Browser', icon: 'globe', route: '/browser', group: 'work' },
  { id: 'tasks', label: 'Tasks', icon: 'checklist', route: '/tasks', group: 'work' },
  { id: 'automation', label: 'Automation', icon: 'run-all', route: '/automation', group: 'work' },
  { id: 'communications', label: 'Communications', icon: 'comment-discussion', route: '/communications', group: 'work' },
  { id: 'task-orchestrator', label: 'Orchestrator', icon: 'graph', route: '/task-orchestrator', group: 'work' },
  { id: 'history', label: 'Activity', icon: 'history', route: '/history', group: 'system' },
  { id: 'extensions', label: 'Extensions', icon: 'extensions', route: '/extensions', group: 'system' },
  { id: 'mcp', label: 'MCP', icon: 'server', route: '/mcp-manager', group: 'system' },
  { id: 'security', label: 'Security', icon: 'shield', route: '/security', group: 'system' },
  { id: 'services', label: 'Services', icon: 'dashboard', route: '/services', group: 'system' },
  { id: 'diagnostics', label: 'Diagnostics', icon: 'check', route: '/diagnostics', group: 'system' },
  // Less frequently used — progressive disclosure under "More"
  { id: 'service-manager', label: 'Services Manager', icon: 'server', route: '/service-manager', group: 'more' },
  { id: 'sandbox', label: 'Sandbox', icon: 'lock', route: '/sandbox', group: 'more' },
  { id: 'workspace-manager', label: 'Workspaces', icon: 'project', route: '/workspace-manager', group: 'more' },
  { id: 'resource-manager', label: 'Resource Manager', icon: 'dashboard', route: '/resource-manager', group: 'system' },
  { id: 'settings', label: 'Settings', icon: 'gear', route: '/settings', group: 'system' },
  { id: 'help', label: 'Help', icon: 'question', route: '/help', group: 'more' },
  { id: 'updates', label: 'Updates', icon: 'refresh', route: '/updates', group: 'more' },
]

export const $activeNavSection = atom<NavSectionId>('home')
export const $sidebarCollapsed = atom(false)
export const $sidebarOpen = atom(true)
export const $sidebarWidth = atom(240)

export function setActiveNavSection(id: NavSectionId) {
  $activeNavSection.set(id)
}

export function toggleSidebarCollapsed() {
  $sidebarCollapsed.set(!$sidebarCollapsed.get())
}

export function setSidebarOpen(open: boolean) {
  $sidebarOpen.set(open)
}
