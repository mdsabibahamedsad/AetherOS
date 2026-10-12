import { atom } from 'nanostores'

import type { DelegationResult, MarketServiceHit } from '@/lib/agent-marketplace-client'

// Agent Marketplace store. IPC-backed only: every value comes from the
// marketplace.* gateway methods (real registry/ledger state). Empty states
// render as empty — reputation shows "insufficient evidence" when the
// backend reports no samples, never invented percentages.

export type MarketSection =
  | 'discover'
  | 'recommended'
  | 'agents'
  | 'services'
  | 'benchmarks'
  | 'reputation'
  | 'contracts'
  | 'transactions'
  | 'budgets'
  | 'disputes'
  | 'security'
  | 'trust'

export const $marketHits = atom<MarketServiceHit[]>([])
export const $marketQuery = atom<string>('')
export const $marketDelegations = atom<DelegationResult[]>([])
export const $marketLedger = atom<Record<string, unknown> | null>(null)
export const $marketBudget = atom<Record<string, unknown> | null>(null)
export const $marketPolicy = atom<Record<string, unknown> | null>(null)
export const $marketLoading = atom<boolean>(false)
export const $marketError = atom<string | null>(null)
export const $marketSection = atom<MarketSection>('discover')
export const $marketStopped = atom<boolean>(false)

export function setMarketHits(hits: MarketServiceHit[]) {
  $marketHits.set(hits)
}

export function setMarketQuery(query: string) {
  $marketQuery.set(query)
}

export function addMarketDelegation(result: DelegationResult) {
  $marketDelegations.set([result, ...$marketDelegations.get()].slice(0, 200))
}

export function setMarketLedger(ledger: Record<string, unknown> | null) {
  $marketLedger.set(ledger)
}

export function setMarketBudget(budget: Record<string, unknown> | null) {
  $marketBudget.set(budget)
}

export function setMarketPolicy(policy: Record<string, unknown> | null) {
  $marketPolicy.set(policy)
}

export function setMarketLoading(loading: boolean) {
  $marketLoading.set(loading)
}

export function setMarketError(error: string | null) {
  $marketError.set(error)
}

export function setMarketSection(section: MarketSection) {
  $marketSection.set(section)
}

export function setMarketStopped(stopped: boolean) {
  $marketStopped.set(stopped)

  if (stopped) {
    $marketError.set('STOP ALL MARKETPLACE ACTIVITY active — new delegations and payments held.')
  } else {
    $marketError.set(null)
  }
}
