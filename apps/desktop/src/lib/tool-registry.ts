import type { ToolsetInfo } from '@/types/aetheros'

import type { RiskTier } from './agi-states'

/**
 * Canonical tool registry (UX layer). Advisory metadata ONLY — enforcement
 * lives server-side (approval gates, sandbox, tool scopes). The registry
 * joins static capability knowledge (what a toolset family does) with live
 * `ToolsetInfo` (enabled/configured/tools) so surfaces show capability +
 * risk without inventing per-tool schemas.
 */

export type ToolCapability =
  | 'read'
  | 'write'
  | 'execute'
  | 'network'
  | 'browser'
  | 'communicate'
  | 'delete'
  | 'system'
  | 'admin'

export type ExecEnvironment = 'workspace' | 'sandbox' | 'system'

export interface ToolsetProfile {
  capabilities: ToolCapability[]
  environments: ExecEnvironment[]
  risk: RiskTier
  /** Timeout callers should assume when the backend reports none. */
  timeoutMs: number
}

const DEFAULT_TIMEOUT_MS = 120_000

const PROFILES: Record<string, ToolsetProfile> = {
  terminal: {
    capabilities: ['execute', 'system'],
    environments: ['sandbox', 'workspace'],
    risk: 'high',
    timeoutMs: DEFAULT_TIMEOUT_MS,
  },
  execute_code: {
    capabilities: ['execute'],
    environments: ['sandbox'],
    risk: 'high',
    timeoutMs: DEFAULT_TIMEOUT_MS,
  },
  filesystem: {
    capabilities: ['read', 'write'],
    environments: ['workspace'],
    risk: 'medium',
    timeoutMs: 30_000,
  },
  file: {
    capabilities: ['read', 'write'],
    environments: ['workspace'],
    risk: 'medium',
    timeoutMs: 30_000,
  },
  browser: {
    capabilities: ['browser', 'network', 'read'],
    environments: ['sandbox'],
    risk: 'medium',
    timeoutMs: DEFAULT_TIMEOUT_MS,
  },
  web: {
    capabilities: ['network', 'read'],
    environments: ['sandbox'],
    risk: 'low',
    timeoutMs: 60_000,
  },
  search: {
    capabilities: ['network', 'read'],
    environments: ['sandbox'],
    risk: 'low',
    timeoutMs: 60_000,
  },
  messaging: {
    capabilities: ['communicate', 'network'],
    environments: ['system'],
    risk: 'high',
    timeoutMs: DEFAULT_TIMEOUT_MS,
  },
  automation: {
    capabilities: ['system', 'execute'],
    environments: ['system'],
    risk: 'medium',
    timeoutMs: DEFAULT_TIMEOUT_MS,
  },
  cron: {
    capabilities: ['system'],
    environments: ['system'],
    risk: 'medium',
    timeoutMs: DEFAULT_TIMEOUT_MS,
  },
  memory: {
    capabilities: ['read', 'write'],
    environments: ['workspace'],
    risk: 'low',
    timeoutMs: 30_000,
  },
  mcp: {
    capabilities: ['execute', 'network'],
    environments: ['sandbox'],
    risk: 'high',
    timeoutMs: DEFAULT_TIMEOUT_MS,
  },
  admin: {
    capabilities: ['admin', 'system'],
    environments: ['system'],
    risk: 'destructive',
    timeoutMs: DEFAULT_TIMEOUT_MS,
  },
}

const FALLBACK_PROFILE: ToolsetProfile = {
  capabilities: [],
  environments: ['sandbox'],
  risk: 'medium',
  timeoutMs: DEFAULT_TIMEOUT_MS,
}

export function toolsetProfile(name: string): ToolsetProfile {
  return PROFILES[name] ?? FALLBACK_PROFILE
}

export interface ToolsetView {
  capabilities: ToolCapability[]
  configured: boolean
  enabled: boolean
  environments: ExecEnvironment[]
  label: string
  name: string
  risk: RiskTier
  toolCount: number
}

/** Join a live toolset with its advisory profile for capability/risk UI. */
export function describeToolset(info: ToolsetInfo): ToolsetView {
  const profile = toolsetProfile(info.name)

  return {
    capabilities: profile.capabilities,
    configured: info.configured,
    enabled: info.enabled,
    environments: profile.environments,
    label: info.label || info.name,
    name: info.name,
    risk: profile.risk,
    toolCount: Array.isArray(info.tools) ? info.tools.length : 0,
  }
}

export const CAPABILITY_LABEL: Record<ToolCapability, string> = {
  read: 'Read',
  write: 'Write',
  execute: 'Execute',
  network: 'Network',
  browser: 'Browser',
  communicate: 'Communicate',
  delete: 'Delete',
  system: 'System',
  admin: 'Admin',
}

export const RISK_LABEL: Record<RiskTier, string> = {
  low: 'Low risk',
  medium: 'Medium risk',
  high: 'High risk',
  destructive: 'Destructive',
}
