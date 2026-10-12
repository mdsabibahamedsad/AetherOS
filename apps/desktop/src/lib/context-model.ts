/**
 * Global context model (UX architecture Phase 27):
 *
 *   GLOBAL → WORKSPACE → APP → TASK → AGENT → ACTION
 *
 * Pure derivation — no new state. Callers pass what they already know
 * (profile, view, session, agents, tool) and get back an ordered chain
 * for breadcrumbs, intent scoping ("this"), and continuity surfaces.
 * Missing layers are omitted, never fabricated.
 */

export type ContextKind = 'global' | 'workspace' | 'app' | 'task' | 'agent' | 'action'

export interface ContextLayer {
  detail?: string | null
  kind: ContextKind
  label: string
  /** Real route where this layer can be opened, when one exists. */
  route?: string | null
}

export interface ContextInput {
  activeAgentCount?: number
  appLabel?: string | null
  appRoute?: string | null
  currentTool?: string | null
  profile?: string | null
  sessionRoute?: string | null
  sessionTitle?: string | null
}

export function buildContextChain(input: ContextInput): ContextLayer[] {
  const chain: ContextLayer[] = [{ kind: 'global', label: 'AetherOS' }]

  if (input.profile && input.profile !== 'default') {
    chain.push({ kind: 'workspace', label: input.profile, route: '/profiles' })
  }

  if (input.appLabel) {
    chain.push({ kind: 'app', label: input.appLabel, route: input.appRoute ?? null })
  }

  if (input.sessionTitle) {
    chain.push({ kind: 'task', label: input.sessionTitle, route: input.sessionRoute ?? null })
  }

  if (typeof input.activeAgentCount === 'number' && input.activeAgentCount > 0) {
    chain.push({
      kind: 'agent',
      label: input.activeAgentCount === 1 ? '1 agent' : `${input.activeAgentCount} agents`,
      route: '/agents',
    })
  }

  if (input.currentTool) {
    chain.push({ kind: 'action', label: input.currentTool })
  }

  return chain
}

/** Compact breadcrumb: "profile › App › Task". Global is the root, not text. */
export function contextSummary(chain: ContextLayer[]): string {
  return chain
    .filter(layer => layer.kind !== 'global')
    .map(layer => layer.label)
    .join(' › ')
}

/**
 * What "this" means for an intent issued at this chain position — the
 * scope an agent should assume, stated so the UI can show it
 * ("Using context from: …") instead of silently injecting memory.
 */
export function scopeDescription(chain: ContextLayer[]): string | null {
  const task = [...chain].reverse().find(layer => layer.kind === 'task' || layer.kind === 'app')
  const workspace = chain.find(layer => layer.kind === 'workspace')

  if (!task) {
    return workspace ? `Workspace ${workspace.label}` : null
  }

  return workspace ? `${task.label} (${workspace.label})` : task.label
}
