import { atom } from 'nanostores'

export type NotificationPriority = 'low' | 'normal' | 'high' | 'urgent'
export type NotificationCategory = 'message' | 'mention' | 'urgent' | 'scheduled' | 'automation' | 'approval' | 'calendar' | 'system' | 'error'

export interface Notification {
  id: string
  title: string
  body: string
  category: NotificationCategory
  priority: NotificationPriority
  provider: string
  conversationId: string
  messageId: string
  read: boolean
  actionUrl: string
  createdAt: string
}

export interface NotificationRule {
  id: string
  name: string
  category: NotificationCategory
  enabled: boolean
  channels: string[]
  priority: NotificationPriority
  sound: string
  quietHoursStart: string
  quietHoursEnd: string
  providerFilter: string
  minPriority: NotificationPriority
}

export interface NotificationsState {
  items: Notification[]
  rules: NotificationRule[]
  unreadCount: number
  filterCategory: NotificationCategory | 'all'
  filterRead: 'all' | 'unread' | 'read'
}

const DEFAULT_RULES: NotificationRule[] = [
  { id: 'rule_msg', name: 'New Messages', category: 'message', enabled: true, channels: ['desktop'], priority: 'normal', sound: 'default', quietHoursStart: '', quietHoursEnd: '', providerFilter: 'all', minPriority: 'low' },
  { id: 'rule_mention', name: 'Mentions', category: 'mention', enabled: true, channels: ['desktop'], priority: 'high', sound: 'alert', quietHoursStart: '', quietHoursEnd: '', providerFilter: 'all', minPriority: 'low' },
  { id: 'rule_urgent', name: 'Urgent Messages', category: 'urgent', enabled: true, channels: ['desktop', 'sound'], priority: 'urgent', sound: 'critical', quietHoursStart: '', quietHoursEnd: '', providerFilter: 'all', minPriority: 'low' },
  { id: 'rule_approval', name: 'Approval Requests', category: 'approval', enabled: true, channels: ['desktop'], priority: 'high', sound: 'alert', quietHoursStart: '', quietHoursEnd: '', providerFilter: 'all', minPriority: 'low' },
  { id: 'rule_automation', name: 'Automation Events', category: 'automation', enabled: true, channels: ['desktop'], priority: 'normal', sound: 'default', quietHoursStart: '', quietHoursEnd: '', providerFilter: 'all', minPriority: 'low' },
  { id: 'rule_error', name: 'Errors & Failures', category: 'error', enabled: true, channels: ['desktop'], priority: 'high', sound: 'alert', quietHoursStart: '', quietHoursEnd: '', providerFilter: 'all', minPriority: 'low' },
  { id: 'rule_scheduled', name: 'Scheduled Messages', category: 'scheduled', enabled: true, channels: ['desktop'], priority: 'normal', sound: 'default', quietHoursStart: '', quietHoursEnd: '', providerFilter: 'all', minPriority: 'low' },
  { id: 'rule_calendar', name: 'Calendar Events', category: 'calendar', enabled: true, channels: ['desktop'], priority: 'normal', sound: 'default', quietHoursStart: '', quietHoursEnd: '', providerFilter: 'all', minPriority: 'low' },
]

const initialState: NotificationsState = {
  items: [],
  rules: DEFAULT_RULES,
  unreadCount: 0,
  filterCategory: 'all',
  filterRead: 'unread',
}

export const $commsNotifications = atom<NotificationsState>(initialState)

const patch = (update: Partial<NotificationsState>) =>
  $commsNotifications.set({ ...$commsNotifications.get(), ...update })

export function setNotificationFilterCategory(cat: NotificationCategory | 'all') { patch({ filterCategory: cat }) }

export function setNotificationFilterRead(filter: 'all' | 'unread' | 'read') { patch({ filterRead: filter }) }

export function addNotification(title: string, body: string, category: NotificationCategory = 'message', priority: NotificationPriority = 'normal', provider = '', conversationId = '', messageId = '') {
  const notif: Notification = {
    id: `notif_${Date.now()}`,
    title,
    body,
    category,
    priority,
    provider,
    conversationId,
    messageId,
    read: false,
    actionUrl: '',
    createdAt: new Date().toISOString(),
  }

  const state = $commsNotifications.get()
  patch({ items: [notif, ...state.items].slice(0, 500), unreadCount: state.unreadCount + 1 })

  return notif
}

export function markNotificationRead(id: string) {
  const state = $commsNotifications.get()
  const items = state.items.map(n => n.id === id ? { ...n, read: true } : n)
  patch({ items, unreadCount: Math.max(0, state.unreadCount - 1) })
}

export function markAllNotificationsRead() {
  const items = $commsNotifications.get().items.map(n => ({ ...n, read: true }))
  patch({ items, unreadCount: 0 })
}

export function getFilteredNotifications() {
  const state = $commsNotifications.get()
  let result = state.items

  if (state.filterCategory !== 'all') {
    result = result.filter(n => n.category === state.filterCategory)
  }

  if (state.filterRead === 'unread') {
    result = result.filter(n => !n.read)
  } else if (state.filterRead === 'read') {
    result = result.filter(n => n.read)
  }

  return result.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
}

export function updateNotificationRule(id: string, updates: Partial<NotificationRule>) {
  const rules = $commsNotifications.get().rules.map(r =>
    r.id === id ? { ...r, ...updates } : r
  )

  patch({ rules })
}

export function clearAllNotifications() {
  patch({ items: [], unreadCount: 0 })
}
