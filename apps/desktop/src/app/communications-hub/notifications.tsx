import { useStore } from '@nanostores/react'
import { useState } from 'react'

import { $commsNotifications, clearAllNotifications, getFilteredNotifications, markAllNotificationsRead, markNotificationRead, setNotificationFilterCategory, setNotificationFilterRead, updateNotificationRule } from '@/store/communications-notifications'
import type { NotificationCategory } from '@/store/communications-notifications'

const CATEGORIES: { id: NotificationCategory | 'all'; label: string; icon: string }[] = [
  { id: 'all', label: 'All', icon: 'globe' },
  { id: 'message', label: 'Messages', icon: 'comment-discussion' },
  { id: 'mention', label: 'Mentions', icon: 'mention' },
  { id: 'urgent', label: 'Urgent', icon: 'warning' },
  { id: 'approval', label: 'Approvals', icon: 'check' },
  { id: 'automation', label: 'Automation', icon: 'run-all' },
  { id: 'error', label: 'Errors', icon: 'error' },
]

export function NotificationsView() {
  const state = useStore($commsNotifications)
  const filtered = getFilteredNotifications()
  const [showSettings, setShowSettings] = useState(false)

  return (
    <div className="flex h-full flex-col">
      <div className="flex shrink-0 items-center justify-between border-b border-(--ui-stroke-tertiary) px-4 py-2">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold">Notifications</h2>
          {state.unreadCount > 0 && (
            <span className="rounded-full bg-primary px-2 py-0.5 text-[10px] text-white">{state.unreadCount}</span>
          )}
        </div>
        <div className="flex gap-1">
          <button className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-(--ui-text-tertiary) hover:bg-(--ui-bg-quaternary)" onClick={markAllNotificationsRead}>
            <span className="codicon codicon-check-all" />
            Mark All Read
          </button>
          <button className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-(--ui-text-tertiary) hover:bg-(--ui-bg-quaternary)" onClick={() => setShowSettings(!showSettings)}>
            <span className="codicon codicon-gear" />
            Settings
          </button>
          <button className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-(--ui-text-tertiary) hover:bg-(--ui-bg-quaternary)" onClick={clearAllNotifications}>
            <span className="codicon codicon-clear-all" />
            Clear All
          </button>
        </div>
      </div>

      {/* Category + Read Filter */}
      <div className="flex shrink-0 items-center gap-2 border-b border-(--ui-stroke-tertiary) px-4 py-2">
        <div className="flex flex-wrap gap-1">
          {CATEGORIES.map(cat => (
            <button
              className={`flex items-center gap-1 rounded-md px-2 py-1 text-xs ${state.filterCategory === cat.id ? 'bg-primary text-white' : 'text-(--ui-text-tertiary) hover:text-foreground'}`}
              key={cat.id}
              onClick={() => setNotificationFilterCategory(cat.id)}
            >
              <span className={`codicon codicon-${cat.icon} text-xs`} />
              {cat.label}
            </button>
          ))}
        </div>
        <div className="ml-auto flex gap-1">
          <button className={`rounded-md px-2 py-1 text-xs ${state.filterRead === 'unread' ? 'bg-(--ui-row-active-background) text-foreground' : 'text-(--ui-text-tertiary)'}`} onClick={() => setNotificationFilterRead('unread')}>Unread</button>
          <button className={`rounded-md px-2 py-1 text-xs ${state.filterRead === 'all' ? 'bg-(--ui-row-active-background) text-foreground' : 'text-(--ui-text-tertiary)'}`} onClick={() => setNotificationFilterRead('all')}>All</button>
          <button className={`rounded-md px-2 py-1 text-xs ${state.filterRead === 'read' ? 'bg-(--ui-row-active-background) text-foreground' : 'text-(--ui-text-tertiary)'}`} onClick={() => setNotificationFilterRead('read')}>Read</button>
        </div>
      </div>

      {/* Notifications List or Settings */}
      {showSettings ? <NotificationSettings /> : (
        <div className="min-h-0 flex-1 overflow-y-auto">
          {filtered.length === 0 ? (
            <div className="flex h-full items-center justify-center text-sm text-(--ui-text-tertiary)">
              <div className="text-center">
                <span className="codicon codicon-bell text-3xl text-(--ui-text-tertiary)" />
                <p className="mt-2">No notifications</p>
              </div>
            </div>
          ) : (
            <div className="divide-y divide-(--ui-stroke-tertiary)">
              {filtered.map(n => (
                <div
                  className={`flex cursor-pointer items-start gap-3 px-4 py-3 transition-colors hover:bg-(--ui-row-hover-background) ${!n.read ? 'bg-(--ui-row-active-background)' : ''}`}
                  key={n.id}
                  onClick={() => markNotificationRead(n.id)}
                >
                  <div className={`flex size-8 shrink-0 items-center justify-center rounded-full ${
                    n.priority === 'urgent' ? 'bg-red-500/20 text-red-500' :
                    n.priority === 'high' ? 'bg-amber-500/20 text-amber-500' :
                    'bg-(--ui-bg-quaternary) text-(--ui-text-tertiary)'
                  }`}>
                    <span className={`codicon codicon-${getCategoryIcon(n.category)} text-sm`} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <span className={`truncate text-xs ${!n.read ? 'font-semibold' : ''}`}>{n.title}</span>
                      <span className="shrink-0 text-[10px] text-(--ui-text-tertiary)">{formatTime(n.createdAt)}</span>
                    </div>
                    <p className="mt-0.5 text-xs text-(--ui-text-tertiary)">{n.body}</p>
                    {n.provider && <span className="mt-0.5 text-[10px] text-(--ui-text-tertiary)">{n.provider}</span>}
                  </div>
                  {!n.read && <div className="mt-1.5 size-2 shrink-0 rounded-full bg-primary" />}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function NotificationSettings() {
  const state = useStore($commsNotifications)

  return (
    <div className="min-h-0 flex-1 overflow-y-auto p-4">
      <div className="max-w-lg space-y-3">
        <h3 className="text-xs font-medium">Notification Rules</h3>
        {state.rules.map(rule => (
          <div className="rounded-lg border border-(--ui-stroke-tertiary) p-3" key={rule.id}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-medium">{rule.name}</p>
                <p className="text-[10px] text-(--ui-text-tertiary)">{rule.category} | {rule.priority} priority</p>
              </div>
              <label className="relative inline-flex cursor-pointer items-center">
                <input
                  checked={rule.enabled}
                  className="peer sr-only"
                  onChange={() => updateNotificationRule(rule.id, { enabled: !rule.enabled })}
                  type="checkbox"
                />
                <div className="h-4 w-7 rounded-full bg-(--ui-bg-quaternary) after:absolute after:left-[2px] after:top-[2px] after:size-3 after:rounded-full after:bg-white after:transition-all peer-checked:bg-primary peer-checked:after:translate-x-full" />
              </label>
            </div>
            <div className="mt-2 flex flex-wrap gap-1">
              {rule.channels.map(ch => (
                <span className="rounded-md bg-(--ui-bg-quaternary) px-1.5 py-0.5 text-[10px] text-(--ui-text-tertiary)" key={ch}>{ch}</span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function getCategoryIcon(category: string): string {
  const icons: Record<string, string> = {
    message: 'comment-discussion', mention: 'mention', urgent: 'warning',
    scheduled: 'clock', automation: 'run-all', approval: 'check',
    calendar: 'calendar', system: 'settings-gear', error: 'error',
  }

  return icons[category] || 'bell'
}

function formatTime(ts: string): string {
  const date = new Date(ts)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  if (diff < 60000) {return 'now'}

  if (diff < 3600000) {return `${Math.floor(diff / 60000)}m`}

  if (diff < 86400000) {return `${Math.floor(diff / 3600000)}h`}

  return date.toLocaleDateString()
}


