import { recall, remember } from './memory'
import { emitEvent, type ObserverEvent, onEvent } from './observer'
import { reason, type ReasoningResult } from './reasoning'

export type AutonomyLevel = 'off' | 'suggestions' | 'semi' | 'full'

let level: AutonomyLevel = 'off'
let enabled = false
let pendingSuggestions: ReasoningResult[] = []
let acceptedCount = 0
let rejectedCount = 0

export function setAutonomy(enabled_: boolean, lvl?: AutonomyLevel): void {
  enabled = enabled_

  if (lvl) {level = lvl}
  remember('preference', 'autonomy.enabled', enabled)
  remember('preference', 'autonomy.level', level)
}

export function isAutonomous(): boolean {
  return enabled && level !== 'off'
}

export function getAutonomyLevel(): AutonomyLevel {
  return level
}

export function getAutonomyState(): { enabled: boolean; level: AutonomyLevel; pending: number; accepted: number; rejected: number } {
  return { enabled, level, pending: pendingSuggestions.length, accepted: acceptedCount, rejected: rejectedCount }
}

export function getPendingSuggestions(): ReasoningResult[] {
  return [...pendingSuggestions]
}

export function acceptSuggestion(index: number): ReasoningResult | null {
  const result = pendingSuggestions[index]

  if (!result) {return null}
  pendingSuggestions.splice(index, 1)
  acceptedCount++

  return result
}

export function rejectSuggestion(index: number): void {
  if (pendingSuggestions[index]) {
    pendingSuggestions.splice(index, 1)
    rejectedCount++
  }
}

export function clearSuggestions(): void {
  pendingSuggestions = []
}

let unsubscribe: (() => void) | null = null

function handleEvent(event: ObserverEvent): void {
  if (!enabled || level === 'off') {return}

  if (level === 'suggestions' && Math.random() > 0.3) {return}

  const result = reason(event)

  if (result) {
    pendingSuggestions.push(result)

    if (pendingSuggestions.length > 20) {pendingSuggestions.shift()}
    emitEvent('autonomy:suggestion', { title: result.suggestions[0]?.title, confidence: result.confidence })
  }
}

export function startAutonomy(): void {
  if (unsubscribe) {return}
  unsubscribe = onEvent('*' as any, handleEvent as any)

  const stored = recall<boolean>('preference', 'autonomy.enabled')

  if (stored !== undefined) {enabled = stored}
  const storedLevel = recall<AutonomyLevel>('preference', 'autonomy.level')

  if (storedLevel) {level = storedLevel}
}

export function stopAutonomy(): void {
  if (unsubscribe) { unsubscribe(); unsubscribe = null }
}
