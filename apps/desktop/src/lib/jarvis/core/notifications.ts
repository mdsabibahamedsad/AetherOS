export type NotificationLevel = 'info' | 'success' | 'warning' | 'error'
export type NotificationSource = 'system' | 'agent' | 'task' | 'autonomy' | 'observer' | 'user'

export interface JarvisNotification {
  id: string
  title: string
  message: string
  level: NotificationLevel
  source: NotificationSource
  timestamp: number
  read: boolean
  dismissible: boolean
  action?: {
    label: string
    handler: string
  }
}

const listeners: Set<(n: JarvisNotification) => void> = new Set()
const history: JarvisNotification[] = []
const MAX_HISTORY = 200
let counter = 0

function nextId(): string {
  return `jarvis_notif_${++counter}_${Date.now().toString(36)}`
}

export function notify(title: string, message: string, level: NotificationLevel = 'info', source: NotificationSource = 'system', opts?: {
  dismissible?: boolean
  actionLabel?: string
  actionHandler?: string
}): JarvisNotification {
  const notification: JarvisNotification = {
    id: nextId(),
    title,
    message,
    level,
    source,
    timestamp: Date.now(),
    read: false,
    dismissible: opts?.dismissible ?? true,
    ...(opts?.actionLabel && opts?.actionHandler ? { action: { label: opts.actionLabel, handler: opts.actionHandler } } : {})
  }

  history.unshift(notification)

  if (history.length > MAX_HISTORY) {history.pop()}

  listeners.forEach(l => l(notification))

  return notification
}

export function onNotification(listener: (n: JarvisNotification) => void): () => void {
  listeners.add(listener)

  return () => listeners.delete(listener)
}

export function getNotifications(limit = 50, unreadOnly = false): JarvisNotification[] {
  let items = history

  if (unreadOnly) {items = items.filter(n => !n.read)}

  return items.slice(0, limit)
}

export function markRead(id: string): void {
  const n = history.find(n => n.id === id)

  if (n) {n.read = true}
}

export function markAllRead(): void {
  history.forEach(n => { n.read = true })
}

export function clearNotifications(): void {
  history.length = 0
}

export function getUnreadCount(): number {
  return history.filter(n => !n.read).length
}

export function getNotificationStats(): { total: number; unread: number; byLevel: Record<string, number> } {
  const byLevel: Record<string, number> = {}
  history.forEach(n => { byLevel[n.level] = (byLevel[n.level] ?? 0) + 1 })

  return { total: history.length, unread: getUnreadCount(), byLevel }
}
