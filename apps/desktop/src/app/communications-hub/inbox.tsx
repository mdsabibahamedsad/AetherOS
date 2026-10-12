import { useStore } from '@nanostores/react'
import { useState } from 'react'

import { $communications, archiveMessage, getFilteredMessages, markMessageRead, setInboxFilter, setInboxSearch, setPlatformFilter, toggleImportantMessage } from '@/store/communications'
import type { CommsPlatformId, InboxFilter, UnifiedMessage } from '@/store/communications'

const FILTERS: { id: InboxFilter; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'unread', label: 'Unread' },
  { id: 'important', label: 'Important' },
  { id: 'pinned', label: 'Pinned' },
  { id: 'ai-only', label: 'AI Replies' },
  { id: 'archived', label: 'Archived' },
]

const PLATFORMS: { id: CommsPlatformId | 'all'; label: string; icon: string }[] = [
  { id: 'all', label: 'All Platforms', icon: 'globe' },
  { id: 'telegram', label: 'Telegram', icon: 'send' },
  { id: 'whatsapp', label: 'WhatsApp', icon: 'message-circle' },
  { id: 'discord', label: 'Discord', icon: 'message-circle' },
  { id: 'slack', label: 'Slack', icon: 'message-square-text' },
  { id: 'gmail', label: 'Gmail', icon: 'mail' },
  { id: 'sms', label: 'SMS', icon: 'message-square-text' },
]

interface InboxViewProps {
  onSelectConversation: (id: string) => void
}

export function InboxView({ onSelectConversation }: InboxViewProps) {
  const comms = useStore($communications)
  const messages = getFilteredMessages()
  const [searchInput, setSearchInput] = useState(comms.inboxSearch)

  const handleSearch = (value: string) => {
    setSearchInput(value)
    setInboxSearch(value)
  }

  return (
    <div className="flex h-full flex-col">
      {/* Search and Filters */}
      <div className="shrink-0 space-y-2 border-b border-(--ui-stroke-tertiary) p-3">
        <div className="relative">
          <span className="codicon codicon-search absolute left-2.5 top-1/2 -translate-y-1/2 text-xs text-(--ui-text-tertiary)" />
          <input
            className="h-8 w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) pl-7 pr-3 text-xs outline-none focus:border-primary"
            onChange={e => handleSearch(e.target.value)}
            placeholder="Search messages..."
            type="text"
            value={searchInput}
          />
        </div>
        <div className="flex flex-wrap gap-1">
          {FILTERS.map(f => (
            <button
              className={`rounded-md px-2.5 py-1 text-xs transition-colors ${
                comms.inboxFilter === f.id
                  ? 'bg-primary text-white'
                  : 'bg-(--ui-bg-quaternary) text-(--ui-text-tertiary) hover:text-foreground'
              }`}
              key={f.id}
              onClick={() => setInboxFilter(f.id)}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap gap-1">
          {PLATFORMS.map(p => (
            <button
              className={`flex items-center gap-1 rounded-md px-2 py-0.5 text-xs transition-colors ${
                comms.selectedPlatformFilter === p.id
                  ? 'bg-(--ui-row-active-background) text-foreground'
                  : 'text-(--ui-text-tertiary) hover:text-foreground'
              }`}
              key={p.id}
              onClick={() => setPlatformFilter(p.id)}
            >
              <span className={`codicon codicon-${p.icon} text-xs`} />
              <span>{p.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Message List */}
      <div className="min-h-0 flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-(--ui-text-tertiary)">
            No messages found
          </div>
        ) : (
          <div className="divide-y divide-(--ui-stroke-tertiary)">
            {messages.map(msg => (
              <MessageRow
                key={msg.id}
                message={msg}
                onSelect={() => onSelectConversation(msg.conversationId)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function MessageRow({ message: msg, onSelect }: { message: UnifiedMessage; onSelect: () => void }) {
  return (
    <div
      className={`flex cursor-pointer items-start gap-3 px-4 py-3 transition-colors hover:bg-(--ui-row-hover-background) ${
        !msg.read ? 'bg-(--ui-row-active-background)' : ''
      }`}
      onClick={() => { markMessageRead(msg.id); onSelect() }}
    >
      <div className={`mt-1 size-2 shrink-0 rounded-full ${msg.priority === 'urgent' ? 'bg-red-500' : msg.priority === 'high' ? 'bg-amber-500' : !msg.read ? 'bg-primary' : 'bg-transparent'}`} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <span className={`truncate text-xs ${!msg.read ? 'font-semibold' : ''}`}>{msg.senderName}</span>
          <span className="shrink-0 text-[10px] text-(--ui-text-tertiary)">
            {formatTime(msg.timestamp)}
          </span>
        </div>
        <p className={`mt-0.5 truncate text-xs ${!msg.read ? 'text-foreground' : 'text-(--ui-text-tertiary)'}`}>
          {msg.content}
        </p>
        <div className="mt-1 flex items-center gap-2">
          <span className="flex items-center gap-0.5 text-[10px] text-(--ui-text-tertiary)">
            <span className={`codicon codicon-${getPlatformIcon(msg.platform)} text-[10px]`} />
            {msg.platform}
          </span>
          {msg.important && <span className="codicon codicon-star-full text-[10px] text-amber-500" />}
          {msg.aiReplied && <span className="codicon codicon-robot text-[10px] text-(--ui-text-tertiary)" />}
          {msg.attachments.length > 0 && <span className="codicon codicon-attach text-[10px] text-(--ui-text-tertiary)" />}
        </div>
      </div>
      <div className="flex shrink-0 flex-col gap-0.5">
        <button
          className={`rounded p-0.5 text-xs transition-colors hover:bg-(--ui-bg-quaternary) ${msg.important ? 'text-amber-500' : 'text-(--ui-text-tertiary)'}`}
          onClick={e => { e.stopPropagation(); toggleImportantMessage(msg.id) }}
        >
          <span className="codicon codicon-star-full" />
        </button>
        <button
          className="rounded p-0.5 text-xs text-(--ui-text-tertiary) transition-colors hover:bg-(--ui-bg-quaternary)"
          onClick={e => { e.stopPropagation(); archiveMessage(msg.id) }}
        >
          <span className="codicon codicon-archive" />
        </button>
      </div>
    </div>
  )
}

function getPlatformIcon(platform: string): string {
  const icons: Record<string, string> = {
    telegram: 'send', whatsapp: 'message-circle', discord: 'message-circle',
    slack: 'message-square-text', gmail: 'mail', outlook: 'mail',
    teams: 'people', signal: 'lock', sms: 'message-square-text',
  }

  return icons[platform] || 'comment-discussion'
}

function formatTime(ts: string): string {
  const date = new Date(ts)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  if (diff < 60000) {return 'now'}

  if (diff < 3600000) {return `${Math.floor(diff / 60000)}m`}

  if (diff < 86400000) {return `${Math.floor(diff / 3600000)}h`}

  if (diff < 604800000) {return `${Math.floor(diff / 86400000)}d`}

  return date.toLocaleDateString()
}
