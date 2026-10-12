import { logAction, markIdle } from './context'

export type ObserverEventType =
  | 'user:activity'
  | 'user:idle'
  | 'clipboard:copy'
  | 'file:open'
  | 'file:save'
  | 'file:create'
  | 'file:delete'
  | 'project:detected'
  | 'git:commit'
  | 'git:branch-change'
  | 'terminal:command'
  | 'browser:url-change'
  | 'app:focus'
  | 'app:open'
  | 'app:close'
  | 'system:resource-high'
  | 'system:resource-normal'
  | 'network:online'
  | 'network:offline'
  | 'error:occurred'
  | 'task:started'
  | 'task:completed'
  | 'task:failed'
  | 'autonomy:suggestion'

export interface ObserverEvent {
  type: ObserverEventType
  data?: Record<string, unknown>
  timestamp: number
}

export type ObserverHandler = (event: ObserverEvent) => void

const handlers: Map<ObserverEventType, Set<ObserverHandler>> = new Map()
const eventLog: ObserverEvent[] = []
const MAX_EVENTS = 200
let pollingId: ReturnType<typeof setInterval> | null = null
let lastActivityTime = Date.now()
const IDLE_THRESHOLD_MS = 120_000

export function onEvent(type: ObserverEventType, handler: ObserverHandler): () => void {
  if (!handlers.has(type)) {handlers.set(type, new Set())}
  handlers.get(type)!.add(handler)

  return () => handlers.get(type)?.delete(handler)
}

export function emitEvent(type: ObserverEventType, data?: Record<string, unknown>): void {
  const event: ObserverEvent = { type, data, timestamp: Date.now() }
  eventLog.unshift(event)

  if (eventLog.length > MAX_EVENTS) {eventLog.pop()}

  handlers.get(type)?.forEach(h => { try { h(event) } catch { /* handler error */ } })

  logAction(`${type}${data ? ' ' + JSON.stringify(data).slice(0, 80) : ''}`)
  lastActivityTime = Date.now()
}

export function getRecentEvents(count = 20): ObserverEvent[] {
  return eventLog.slice(0, count)
}

export function startObserver(pollMs = 5000): void {
  if (pollingId) {return}
  pollingId = setInterval(() => {
    const now = Date.now()

    if (now - lastActivityTime > IDLE_THRESHOLD_MS) {
      markIdle()
      emitEvent('user:idle', { duration: now - lastActivityTime })
    }
  }, pollMs)
}

export function stopObserver(): void {
  if (pollingId) { clearInterval(pollingId); pollingId = null }
}

export function recordUserActivity(): void {
  lastActivityTime = Date.now()
}

export function simulateEvent(type: ObserverEventType, data?: Record<string, unknown>): void {
  emitEvent(type, data)
}
