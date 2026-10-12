import { atom } from 'nanostores'

import type { NetworkAgent, NetworkTask } from '@/lib/agent-network-client'

// Agent Network store. IPC-backed only: every value comes from the
// agent.network.* gateway methods (real registry state). Unknown health
// renders as unknown — never as online — and discovered agents render as
// UNTRUSTED until verification + explicit approval succeed.

export type NetworkSection =
  | 'network'
  | 'discover'
  | 'trusted'
  | 'local'
  | 'organization'
  | 'remote'
  | 'tasks'
  | 'trust'
  | 'security'
  | 'activity'

export const $networkAgents = atom<NetworkAgent[]>([])
export const $networkTasks = atom<NetworkTask[]>([])
export const $networkEvents = atom<Record<string, unknown>[]>([])
export const $networkSecurity = atom<Record<string, unknown> | null>(null)
export const $networkLoading = atom<boolean>(false)
export const $networkError = atom<string | null>(null)
export const $networkSection = atom<NetworkSection>('network')
export const $selectedAgentId = atom<string | null>(null)
export const $emergencyStopped = atom<boolean>(false)

export function setNetworkAgents(agents: NetworkAgent[]) {
  $networkAgents.set(agents)
}

export function setNetworkTasks(tasks: NetworkTask[]) {
  $networkTasks.set(tasks)
}

export function setNetworkEvents(events: Record<string, unknown>[]) {
  $networkEvents.set(events.slice(0, 1000))
}

export function setNetworkSecurity(summary: Record<string, unknown> | null) {
  $networkSecurity.set(summary)
}

export function setNetworkLoading(loading: boolean) {
  $networkLoading.set(loading)
}

export function setNetworkError(error: string | null) {
  $networkError.set(error)
}

export function setNetworkSection(section: NetworkSection) {
  $networkSection.set(section)
}

export function selectAgent(id: string | null) {
  $selectedAgentId.set(id)
}

export function trustedAgents(): NetworkAgent[] {
  return $networkAgents
    .get()
    .filter(a => ['user_trusted', 'organization_trusted', 'fully_trusted'].includes(a.trust))
}

export function pendingAgents(): NetworkAgent[] {
  return $networkAgents
    .get()
    .filter(a => !['user_trusted', 'organization_trusted', 'fully_trusted', 'blocked', 'revoked'].includes(a.trust))
}

export function blockedAgents(): NetworkAgent[] {
  return $networkAgents.get().filter(a => ['blocked', 'revoked'].includes(a.trust))
}

export function setEmergencyStopped(stopped: boolean) {
  $emergencyStopped.set(stopped)

  if (stopped) {
    // Local kill-switch: hold new delegation in the UI. The gateway's
    // trust/revocation state remains authoritative for in-flight tasks.
    $networkError.set('STOP ALL REMOTE AGENTS active — new delegation held in UI.')
  } else {
    $networkError.set(null)
  }
}
