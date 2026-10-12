import { beforeEach, describe, expect, it } from 'vitest'

import {
  $commsNotifications, addNotification, clearAllNotifications,
  getFilteredNotifications, markAllNotificationsRead, markNotificationRead,
  setNotificationFilterCategory, setNotificationFilterRead, updateNotificationRule,
} from './communications-notifications'

describe('communications-notifications store', () => {
  beforeEach(() => {
    $commsNotifications.set({
      items: [],
      rules: [],
      unreadCount: 0,
      filterCategory: 'all',
      filterRead: 'unread',
    })
  })

  it('adds a notification', () => {
    addNotification('Test Title', 'Test body', 'message', 'normal', 'telegram')
    expect($commsNotifications.get().items).toHaveLength(1)
    expect($commsNotifications.get().unreadCount).toBe(1)
    expect($commsNotifications.get().items[0].title).toBe('Test Title')
  })

  it('marks notification as read', () => {
    addNotification('Title', 'Body')
    const id = $commsNotifications.get().items[0].id
    markNotificationRead(id)
    expect($commsNotifications.get().items[0].read).toBe(true)
    expect($commsNotifications.get().unreadCount).toBe(0)
  })

  it('marks all notifications as read', () => {
    addNotification('A', 'Body A')
    addNotification('B', 'Body B')
    markAllNotificationsRead()
    expect($commsNotifications.get().items.every(n => n.read)).toBe(true)
    expect($commsNotifications.get().unreadCount).toBe(0)
  })

  it('filters notifications by category', () => {
    addNotification('Msg', 'Body', 'message', 'normal', 'telegram')
    addNotification('Err', 'Error body', 'error', 'high', '')
    addNotification('Urg', 'Urgent!', 'urgent', 'urgent', '')
    setNotificationFilterCategory('error')
    const filtered = getFilteredNotifications()
    expect(filtered).toHaveLength(1)
    expect(filtered[0].title).toBe('Err')
  })

  it('filters by read status', () => {
    addNotification('Test', 'Body')
    setNotificationFilterRead('unread')
    expect(getFilteredNotifications()).toHaveLength(1)
    markNotificationRead($commsNotifications.get().items[0].id)
    setNotificationFilterRead('read')
    expect(getFilteredNotifications()).toHaveLength(1)
  })

  it('updates a notification rule', () => {
    const rule = { id: 'rule_test', name: 'Test Rule', category: 'message' as const, enabled: true, channels: ['desktop'], priority: 'normal' as const, sound: 'default', quietHoursStart: '', quietHoursEnd: '', providerFilter: 'all', minPriority: 'low' as const }
    $commsNotifications.set({ ...$commsNotifications.get(), rules: [rule] })
    updateNotificationRule('rule_test', { enabled: false })
    expect($commsNotifications.get().rules[0].enabled).toBe(false)
  })

  it('clears all notifications', () => {
    addNotification('A', 'Body A')
    addNotification('B', 'Body B')
    clearAllNotifications()
    expect($commsNotifications.get().items).toHaveLength(0)
    expect($commsNotifications.get().unreadCount).toBe(0)
  })
})
