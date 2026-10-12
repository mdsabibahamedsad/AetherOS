import { useStore } from '@nanostores/react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'
import {
  $communications,
  archiveMessage,
  type CommsPlatformId,
  getFilteredMessages,
  getPlatformMeta,
  type InboxFilter,
  markMessageRead,
  selectConversation,
  setInboxFilter,
  setInboxSearch,
  setPlatformFilter,
  toggleImportantMessage,
  togglePinMessage,
  type UnifiedMessage
} from '@/store/communications'

const FILTERS: { id: InboxFilter; label: string; count: (msgs: UnifiedMessage[]) => number }[] = [
  { id: 'all', label: 'All', count: msgs => msgs.filter(m => !m.archived).length },
  { id: 'unread', label: 'Unread', count: msgs => msgs.filter(m => !m.read && !m.archived).length },
  { id: 'important', label: 'Important', count: msgs => msgs.filter(m => m.important).length },
  { id: 'pinned', label: 'Pinned', count: msgs => msgs.filter(m => m.pinned).length },
  { id: 'ai-only', label: 'AI Only', count: msgs => msgs.filter(m => m.aiReplied).length },
  { id: 'archived', label: 'Archived', count: msgs => msgs.filter(m => m.archived).length }
]

const PLATFORMS: { id: CommsPlatformId | 'all'; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'telegram', label: 'Telegram' },
  { id: 'whatsapp', label: 'WhatsApp' },
  { id: 'discord', label: 'Discord' },
  { id: 'slack', label: 'Slack' },
  { id: 'gmail', label: 'Gmail' },
  { id: 'outlook', label: 'Outlook' },
  { id: 'teams', label: 'Teams' },
  { id: 'signal', label: 'Signal' },
  { id: 'sms', label: 'SMS' },
  { id: 'webhook', label: 'Webhook' }
]

export function UnifiedInbox() {
  const state = useStore($communications)
  const filtered = getFilteredMessages()
  const totalFilterCount = FILTERS.find(f => f.id === state.inboxFilter)

  const selectedMsg = state.selectedConversation
    ? state.messages.find(m => m.conversationId === state.selectedConversation)
    : null

  return (
    <div className="flex h-full min-h-0">
      <div className="flex w-72 min-w-0 shrink-0 flex-col border-r border-(--ui-stroke-tertiary)">
        <div className="flex shrink-0 flex-col gap-2 border-b border-(--ui-stroke-tertiary) px-3 py-2">
          <Input
            className="h-7 text-xs"
            onChange={e => setInboxSearch(e.target.value)}
            placeholder="Search messages..."
            value={state.inboxSearch}
          />
          <div className="flex flex-wrap gap-1">
            {PLATFORMS.slice(0, 6).map(p => (
              <button
                className={cn(
                  'rounded px-1.5 py-0.5 text-[0.65rem] font-medium transition-colors',
                  state.selectedPlatformFilter === p.id
                    ? 'bg-primary/10 text-primary'
                    : 'text-(--ui-text-tertiary) hover:text-foreground'
                )}
                key={p.id}
                onClick={() => setPlatformFilter(p.id)}
                type="button"
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>
        <div className="flex shrink-0 gap-0.5 border-b border-(--ui-stroke-tertiary) px-2 py-1.5">
          {FILTERS.map(f => (
            <button
              className={cn(
                'rounded px-1.5 py-0.5 text-[0.65rem] font-medium transition-colors',
                state.inboxFilter === f.id
                  ? 'bg-primary/10 text-primary'
                  : 'text-(--ui-text-tertiary) hover:text-foreground'
              )}
              key={f.id}
              onClick={() => setInboxFilter(f.id)}
              type="button"
            >
              {f.label}
              <span className="ml-1 opacity-60">{f.count(state.messages)}</span>
            </button>
          ))}
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto">
          {filtered.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <p className="text-xs text-(--ui-text-tertiary)">No messages</p>
            </div>
          )}
          {filtered.map(msg => (
            <MessageRow
              key={msg.id}
              message={msg}
              onSelect={() => {
                selectConversation(msg.conversationId)
                markMessageRead(msg.id)
              }}
              selected={msg.conversationId === state.selectedConversation}
            />
          ))}
        </div>
      </div>
      <div className="flex min-h-0 flex-1 flex-col">
        {selectedMsg ? (
          <ConversationDetail message={selectedMsg} />
        ) : (
          <div className="flex flex-1 items-center justify-center">
            <p className="text-sm text-(--ui-text-tertiary)">Select a conversation</p>
          </div>
        )}
      </div>
    </div>
  )
}

function MessageRow({ message, selected, onSelect }: { message: UnifiedMessage; selected: boolean; onSelect: () => void }) {
  const meta = getPlatformMeta(message.platform)

  return (
    <button
      className={cn(
        'flex w-full flex-col gap-0.5 border-b border-(--ui-stroke-tertiary) px-3 py-2 text-left transition-colors',
        selected && 'bg-(--ui-row-active-background)',
        !message.read && !selected && 'bg-primary/[0.02]'
      )}
      onClick={onSelect}
      type="button"
    >
      <div className="flex items-center gap-2">
        <span
          className="inline-grid size-5 shrink-0 place-items-center rounded text-[0.55rem] font-bold"
          style={{ backgroundColor: `color-mix(in srgb, ${meta?.color ?? '#71717A'} 20%, transparent)`, color: meta?.color ?? '#71717A' }}
        >
          {meta?.name[0] ?? '?'}
        </span>
        <span className={cn('min-w-0 flex-1 truncate text-sm', !message.read && 'font-semibold')}>
          {message.senderName}
        </span>
        <span className="shrink-0 text-[0.6rem] text-(--ui-text-tertiary)">
          {formatTime(message.timestamp)}
        </span>
      </div>
      <p className={cn('truncate pl-7 text-xs', message.read ? 'text-(--ui-text-tertiary)' : 'text-foreground')}>
        {message.content}
      </p>
      <div className="flex items-center gap-1.5 pl-7">
        {message.important && <span className="text-[0.55rem] text-amber-500">★</span>}
        {message.aiReplied && <Badge className="px-1 py-0 text-[0.5rem]" variant="default">AI</Badge>}
        {message.pinned && <span className="text-[0.55rem] text-(--ui-text-tertiary)">📌</span>}
        {message.direction === 'outgoing' && (
          <span className="text-[0.55rem] text-(--ui-text-tertiary)">
            {message.status === 'sent' && '✓'}
            {message.status === 'delivered' && '✓✓'}
            {message.status === 'read' && '✓✓'}
            {message.status === 'failed' && '✗'}
          </span>
        )}
      </div>
    </button>
  )
}

function ConversationDetail({ message }: { message: UnifiedMessage }) {
  const meta = getPlatformMeta(message.platform)
  const allMessages = useStore($communications).messages.filter(m => m.conversationId === message.conversationId)

  return (
    <>
      <div className="flex shrink-0 items-center gap-3 border-b border-(--ui-stroke-tertiary) px-4 py-2.5">
        <div className="flex items-center gap-2">
          <span
            className="inline-grid size-6 place-items-center rounded text-[0.6rem] font-bold"
            style={{ backgroundColor: `color-mix(in srgb, ${meta?.color ?? '#71717A'} 20%, transparent)`, color: meta?.color ?? '#71717A' }}
          >
            {meta?.name[0] ?? '?'}
          </span>
          <span className="text-sm font-medium">{message.senderName}</span>
        </div>
        <span className="text-xs text-(--ui-text-tertiary)">{meta?.name}</span>
        <div className="ml-auto flex items-center gap-1">
          <Button onClick={() => toggleImportantMessage(message.id)} size="xs" variant="ghost">
            {message.important ? '★' : '☆'}
          </Button>
          <Button onClick={() => togglePinMessage(message.id)} size="xs" variant="ghost">
            {message.pinned ? '📌' : '📍'}
          </Button>
          <Button onClick={() => archiveMessage(message.id)} size="xs" variant="ghost">
            🗑
          </Button>
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-3">
        {allMessages.map(msg => (
          <div className={cn('mb-3 flex', msg.direction === 'outgoing' ? 'justify-end' : 'justify-start')} key={msg.id}>
            <div
              className={cn(
                'max-w-[70%] rounded-lg px-3 py-2',
                msg.direction === 'outgoing'
                  ? 'bg-primary/10 text-foreground'
                  : 'bg-(--ui-row-active-background) text-foreground'
              )}
            >
              <p className="text-sm">{msg.content}</p>
              <div className="mt-1 flex items-center justify-end gap-1">
                <span className="text-[0.55rem] text-(--ui-text-tertiary)">{formatTime(msg.timestamp)}</span>
                {msg.direction === 'outgoing' && (
                  <span className="text-[0.55rem] text-(--ui-text-tertiary)">
                    {msg.status === 'sent' && '✓'}
                    {msg.status === 'delivered' && '✓✓'}
                    {msg.status === 'read' && '✓✓'}
                    {msg.status === 'failed' && '✗'}
                  </span>
                )}
              </div>
              {msg.aiReplied && msg.aiResponse && (
                <div className="mt-2 rounded-md border border-primary/20 bg-primary/5 px-2 py-1.5">
                  <span className="text-[0.6rem] font-medium text-primary">AI Reply</span>
                  <p className="mt-0.5 text-xs text-(--ui-text-secondary)">{msg.aiResponse}</p>
                </div>
              )}
              {msg.attachments.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {msg.attachments.map((att, i) => (
                    <span className="rounded bg-(--ui-row-active-background) px-1.5 py-0.5 text-[0.55rem] text-(--ui-text-tertiary)" key={i}>
                      {att.type} · {att.name}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </>
  )
}

function formatTime(timestamp: string): string {
  const d = new Date(timestamp)
  const now = new Date()
  const isToday = d.toDateString() === now.toDateString()

  if (isToday) {return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}

  return d.toLocaleDateString([], { month: 'short', day: 'numeric' })
}
