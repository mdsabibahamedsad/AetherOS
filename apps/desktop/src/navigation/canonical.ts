/**
 * AetherOS canonical navigation registry (Master 63 §7 — Information Architecture).
 *
 * The full route table lives in `@/app/routes`; this registry is the curated,
 * product-level IA: the top-level areas a user can navigate to, grouped for
 * progressive disclosure. Every entry MUST point at a real route constant —
 * no dead destinations. Advanced/internal subsystems stay reachable via
 * command palette / search / settings, not via primary navigation.
 */

import {
  AGENT_MARKETPLACE_ROUTE,
  AGENT_NETWORK_ROUTE,
  ARTIFACTS_ROUTE,
  AUTOMATION_CENTER_ROUTE,
  AUTOMATION_ROUTE,
  BROWSER_ROUTE,
  COMMAND_CENTER_ROUTE,
  COMPUTER_USE_ROUTE,
  CRON_ROUTE,
  DEVELOPER_TOOLS_ROUTE,
  DEVICES_ROUTE,
  EXTENSION_SDK_ROUTE,
  HISTORY_ROUTE,
  HOME_ROUTE,
  KNOWLEDGE_ROUTE,
  MARKETPLACE_ROUTE,
  MCP_MANAGER_ROUTE,
  MEMORY_ROUTE,
  MODELS_ROUTE,
  NEW_CHAT_ROUTE,
  PROFILES_ROUTE,
  SECURITY_CENTER_ROUTE,
  SETTINGS_ROUTE,
  SWARM_CENTER_ROUTE,
  SYNC_DASHBOARD_ROUTE,
  TASKS_ROUTE,
} from '@/app/routes'

export type NavVisibility = 'primary' | 'secondary' | 'advanced'

export interface CanonicalNavEntry {
  /** Stable, agent-readable identifier (Master 63 §70). */
  id: string
  label: string
  /** Human-readable description for palettes and tooltips. */
  description: string
  /** Real route path — must resolve in APP_ROUTES. */
  path: string
  /** Codicon name for the icon system (Master 63 §80). */
  icon: string
  visibility: NavVisibility
  /** Keyboard shortcut hint where one exists (informational only). */
  shortcut?: string
}

export interface CanonicalNavGroup {
  id: string
  label: string
  entries: CanonicalNavEntry[]
}

/**
 * Canonical top-level areas (§7), curated — not every internal subsystem is a
 * primary destination. Groups render in order; `advanced` groups collapse
 * behind progressive disclosure.
 */
export const CANONICAL_NAV: readonly CanonicalNavGroup[] = [
  {
    id: 'workspace',
    label: 'Workspace',
    entries: [
      { id: 'home', label: 'Home', description: 'What is happening — live operational state', path: HOME_ROUTE, icon: 'home', visibility: 'primary' },
      { id: 'chat', label: 'Agent', description: 'Natural-language command surface + collaboration', path: NEW_CHAT_ROUTE, icon: 'comment-discussion', visibility: 'primary', shortcut: 'Ctrl+K' },
      { id: 'tasks', label: 'Tasks', description: 'First-class task objects and their execution', path: TASKS_ROUTE, icon: 'checklist', visibility: 'primary' },
      { id: 'command-center', label: 'Activity', description: 'Unified activity stream across subsystems', path: COMMAND_CENTER_ROUTE, icon: 'pulse', visibility: 'primary' },
    ],
  },
  {
    id: 'execute',
    label: 'Execute',
    entries: [
      { id: 'computer', label: 'Computer', description: 'Computer-use sessions with takeover control', path: COMPUTER_USE_ROUTE, icon: 'keyboard', visibility: 'primary' },
      { id: 'browser', label: 'Browser', description: 'Agent/user-shared browser workspace', path: BROWSER_ROUTE, icon: 'globe', visibility: 'primary' },
      { id: 'research', label: 'Research', description: 'Research jobs with evidence and citations', path: KNOWLEDGE_ROUTE, icon: 'book', visibility: 'primary' },
      { id: 'automation', label: 'Automations', description: 'Schedules, triggers, and automation history', path: AUTOMATION_CENTER_ROUTE, icon: 'zap', visibility: 'secondary' },
      { id: 'cron', label: 'Schedules', description: 'Cron job schedules and run history', path: CRON_ROUTE, icon: 'clock', visibility: 'secondary' },
      { id: 'swarm', label: 'Swarm', description: 'Multi-agent runs, roles, and shared context', path: SWARM_CENTER_ROUTE, icon: 'organization', visibility: 'secondary' },
    ],
  },
  {
    id: 'system',
    label: 'System',
    entries: [
      { id: 'memory', label: 'Memory', description: 'Inspectable, revocable memory with provenance', path: MEMORY_ROUTE, icon: 'database', visibility: 'primary' },
      { id: 'models', label: 'Models', description: 'Model resources, availability, and routing', path: MODELS_ROUTE, icon: 'cpu', visibility: 'primary' },
      { id: 'artifacts', label: 'Artifacts', description: 'Universal artifact browser with provenance', path: ARTIFACTS_ROUTE, icon: 'package', visibility: 'secondary' },
      { id: 'mcp', label: 'MCP', description: 'MCP servers, trust, permissions, and health', path: MCP_MANAGER_ROUTE, icon: 'plug', visibility: 'secondary' },
      { id: 'a2a', label: 'A2A', description: 'Remote agents, pairings, and trust state', path: AGENT_NETWORK_ROUTE, icon: 'network', visibility: 'secondary' },
      { id: 'security', label: 'Security', description: 'Approvals, policies, audit, and trust', path: SECURITY_CENTER_ROUTE, icon: 'shield', visibility: 'primary' },
    ],
  },
  {
    id: 'build',
    label: 'Build',
    entries: [
      { id: 'marketplace', label: 'Marketplace', description: 'Extensions and agent packages with permission preview', path: MARKETPLACE_ROUTE, icon: 'extensions', visibility: 'secondary' },
      { id: 'agent-marketplace', label: 'Agent Marketplace', description: 'Agent services, contracts, and budgets', path: AGENT_MARKETPLACE_ROUTE, icon: 'globe', visibility: 'advanced' },
      { id: 'developer', label: 'Developer', description: 'SDK, API explorer, logs, traces, and packages', path: DEVELOPER_TOOLS_ROUTE, icon: 'code', visibility: 'advanced' },
      { id: 'extension-sdk', label: 'Extension SDK', description: 'Extension authoring surface', path: EXTENSION_SDK_ROUTE, icon: 'tools', visibility: 'advanced' },
      { id: 'legacy-automation', label: 'Automation (legacy)', description: 'Legacy automation view — prefer Automations', path: AUTOMATION_ROUTE, icon: 'zap', visibility: 'advanced' },
      { id: 'history', label: 'History', description: 'Session and run history', path: HISTORY_ROUTE, icon: 'history', visibility: 'advanced' },
    ],
  },
  {
    id: 'manage',
    label: 'Manage',
    entries: [
      { id: 'devices', label: 'Devices', description: 'Registered devices and their connection state', path: DEVICES_ROUTE, icon: 'device-mobile', visibility: 'secondary' },
      { id: 'sync', label: 'Sync & Backup', description: 'Backup health, sync state, and conflicts', path: SYNC_DASHBOARD_ROUTE, icon: 'sync', visibility: 'secondary' },
      { id: 'profiles', label: 'Workspaces', description: 'Profiles and project-level context', path: PROFILES_ROUTE, icon: 'account', visibility: 'secondary' },
      { id: 'settings', label: 'Settings', description: 'Goal-oriented settings with search', path: SETTINGS_ROUTE, icon: 'gear', visibility: 'primary' },
    ],
  },
] as const

/** Flat lookup by stable id. */
export function canonicalNavEntry(id: string): CanonicalNavEntry | null {
  for (const group of CANONICAL_NAV) {
    const found = group.entries.find(e => e.id === id)

    if (found) {
      return found
    }
  }

  return null
}

/** Primary-destination ids for the sidebar / top-level chrome. */
export function primaryNavEntries(): CanonicalNavEntry[] {
  return CANONICAL_NAV.flatMap(g => g.entries).filter(e => e.visibility === 'primary')
}
