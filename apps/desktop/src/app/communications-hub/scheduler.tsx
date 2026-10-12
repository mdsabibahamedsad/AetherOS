import { useStore } from '@nanostores/react'
import { useState } from 'react'

import { $contacts } from '@/store/communications-contacts'
import { $scheduler, approveScheduledMessage, cancelScheduledMessage, getFilteredScheduledMessages, pauseScheduledMessage, rescheduleMessage, resumeScheduledMessage, scheduleMessage, setSchedulerFilter } from '@/store/communications-scheduler'
import type { ScheduledMessage } from '@/store/communications-scheduler'

export function SchedulerView() {
  const scheduler = useStore($scheduler)
  const contacts = useStore($contacts)
  const messages = getFilteredScheduledMessages()
  const [showSchedule, setShowSchedule] = useState(false)
  const [content, setContent] = useState('')
  const [recipientId, setRecipientId] = useState('')
  const [recipientName, setRecipientName] = useState('')
  const [provider, setProvider] = useState('telegram')
  const [date, setDate] = useState('')
  const [time, setTime] = useState('')
  const [recurrence, setRecurrence] = useState<'none' | 'daily' | 'weekly' | 'monthly'>('none')
  const [requireApproval, setRequireApproval] = useState(true)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editContent, setEditContent] = useState('')

  const handleSchedule = () => {
    if (!content.trim() || !date || !time) {return}
    scheduleMessage({
      provider,
      accountId: '',
      recipientId,
      recipientName: recipientName || recipientId,
      content: content.trim(),
      scheduledAt: `${date}T${time}:00`,
      status: 'scheduled',
      recurrence: recurrence === 'none' ? 'none' : recurrence,
      recurrenceConfig: {},
      attachments: [],
      requireApproval,
      approved: !requireApproval,
      templateId: '',
      parentId: '',
      sentAt: '',
      errorMessage: '',
      createdBy: 'user',
    })
    setShowSchedule(false)
    setContent('')
    setRecipientId('')
    setRecipientName('')
    setDate('')
    setTime('')
  }

  const handleReschedule = (id: string) => {
    const newDate = prompt('New date (YYYY-MM-DD):')
    const newTime = prompt('New time (HH:MM):')

    if (newDate && newTime) {
      rescheduleMessage(id, `${newDate}T${newTime}:00`)
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex shrink-0 items-center justify-between border-b border-(--ui-stroke-tertiary) px-4 py-2">
        <div className="flex gap-1">
          <button className={`rounded-md px-2.5 py-1 text-xs ${scheduler.viewFilter === 'upcoming' ? 'bg-primary text-white' : 'text-(--ui-text-tertiary) hover:text-foreground'}`} onClick={() => setSchedulerFilter('upcoming')}>Upcoming</button>
          <button className={`rounded-md px-2.5 py-1 text-xs ${scheduler.viewFilter === 'all' ? 'bg-primary text-white' : 'text-(--ui-text-tertiary) hover:text-foreground'}`} onClick={() => setSchedulerFilter('all')}>All</button>
          <button className={`rounded-md px-2.5 py-1 text-xs ${scheduler.viewFilter === 'history' ? 'bg-primary text-white' : 'text-(--ui-text-tertiary) hover:text-foreground'}`} onClick={() => setSchedulerFilter('history')}>History</button>
        </div>
        <button className="flex items-center gap-1 rounded-md bg-primary px-3 py-1.5 text-xs text-white" onClick={() => setShowSchedule(!showSchedule)}>
          <span className="codicon codicon-add" />
          Schedule Message
        </button>
      </div>

      {/* Schedule Form */}
      {showSchedule && (
        <div className="shrink-0 border-b border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) p-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-(--ui-text-tertiary)">Provider</label>
              <select className="h-8 w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-2 text-xs outline-none" onChange={e => setProvider(e.target.value)} value={provider}>
                <option value="telegram">Telegram</option>
                <option value="whatsapp">WhatsApp</option>
                <option value="discord">Discord</option>
                <option value="slack">Slack</option>
                <option value="gmail">Gmail</option>
                <option value="sms">SMS</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-(--ui-text-tertiary)">Recipient</label>
              <input className="h-8 w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-2 text-xs outline-none" onChange={e => setRecipientId(e.target.value)} placeholder="Username or ID" type="text" value={recipientId} />
            </div>
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-(--ui-text-tertiary)">Recipient Name</label>
              <input className="h-8 w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-2 text-xs outline-none" onChange={e => setRecipientName(e.target.value)} placeholder="Display name" type="text" value={recipientName} />
            </div>
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-(--ui-text-tertiary)">Recurrence</label>
              <select className="h-8 w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-2 text-xs outline-none" onChange={e => setRecurrence(e.target.value as any)} value={recurrence}>
                <option value="none">None</option>
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-(--ui-text-tertiary)">Date</label>
              <input className="h-8 w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-2 text-xs outline-none" onChange={e => setDate(e.target.value)} type="date" value={date} />
            </div>
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-(--ui-text-tertiary)">Time</label>
              <input className="h-8 w-full rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) px-2 text-xs outline-none" onChange={e => setTime(e.target.value)} type="time" value={time} />
            </div>
          </div>
          <div className="mt-2">
            <textarea
              className="w-full resize-none rounded-md border border-(--ui-stroke-tertiary) bg-(--ui-bg-quaternary) p-2 text-xs outline-none focus:border-primary"
              onChange={e => setContent(e.target.value)}
              placeholder="Message content..."
              rows={3}
              value={content}
            />
          </div>
          <div className="mt-2 flex items-center justify-between">
            <label className="flex items-center gap-2 text-xs">
              <input checked={requireApproval} className="rounded" onChange={e => setRequireApproval(e.target.checked)} type="checkbox" />
              Require approval before sending
            </label>
            <div className="flex gap-2">
              <button className="rounded-md px-3 py-1.5 text-xs text-(--ui-text-tertiary) hover:bg-(--ui-bg-quaternary)" onClick={() => setShowSchedule(false)}>Cancel</button>
              <button className="rounded-md bg-primary px-3 py-1.5 text-xs text-white" onClick={handleSchedule}>Schedule</button>
            </div>
          </div>
        </div>
      )}

      {/* Message List */}
      <div className="min-h-0 flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-(--ui-text-tertiary)">No scheduled messages</div>
        ) : (
          <div className="divide-y divide-(--ui-stroke-tertiary)">
            {messages.map(msg => (
              <ScheduledMessageRow
                key={msg.id}
                message={msg}
                onApprove={() => approveScheduledMessage(msg.id)}
                onCancel={() => cancelScheduledMessage(msg.id)}
                onPause={() => pauseScheduledMessage(msg.id)}
                onReschedule={() => handleReschedule(msg.id)}
                onResume={() => resumeScheduledMessage(msg.id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function ScheduledMessageRow({ message: msg, onCancel, onPause, onResume, onReschedule, onApprove }: {
  message: ScheduledMessage; onCancel: () => void; onPause: () => void; onResume: () => void
  onReschedule: () => void; onApprove: () => void
}) {
  const statusColors: Record<string, string> = {
    scheduled: 'text-blue-500', sent: 'text-green-500', failed: 'text-red-500',
    cancelled: 'text-(--ui-text-tertiary)', paused: 'text-amber-500', pending: 'text-(--ui-text-tertiary)',
  }

  return (
    <div className="flex items-start gap-3 px-4 py-3">
      <div className={`mt-1 size-2 shrink-0 rounded-full ${statusColors[msg.status]?.replace('text-', 'bg-') || 'bg-(--ui-text-tertiary)'}`} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium">{msg.recipientName}</span>
          <span className="text-[10px] text-(--ui-text-tertiary)">via {msg.provider}</span>
          {msg.recurrence !== 'none' && (
            <span className="rounded-md bg-(--ui-bg-quaternary) px-1.5 py-0.5 text-[10px] text-(--ui-text-tertiary)">{msg.recurrence}</span>
          )}
        </div>
        <p className="mt-0.5 text-xs text-(--ui-text-tertiary)">{msg.content}</p>
        <div className="mt-1 flex items-center gap-2 text-[10px] text-(--ui-text-tertiary)">
          <span className="codicon codicon-clock" />
          {new Date(msg.scheduledAt).toLocaleString()}
          {msg.status === 'scheduled' && !msg.approved && msg.requireApproval && (
            <span className="rounded-md bg-amber-500/10 px-1.5 py-0.5 text-amber-500">Needs approval</span>
          )}
        </div>
      </div>
      <div className="flex shrink-0 gap-1">
        {msg.status === 'scheduled' && (
          <>
            {msg.requireApproval && !msg.approved && (
              <button className="rounded-md bg-green-500 px-2 py-1 text-xs text-white" onClick={onApprove}>Approve</button>
            )}
            <button className="rounded-md bg-(--ui-bg-quaternary) px-2 py-1 text-xs" onClick={onPause}>Pause</button>
            <button className="rounded-md bg-(--ui-bg-quaternary) px-2 py-1 text-xs" onClick={onReschedule}>Edit</button>
            <button className="rounded-md bg-red-500/10 px-2 py-1 text-xs text-red-500" onClick={onCancel}>Cancel</button>
          </>
        )}
        {msg.status === 'paused' && <button className="rounded-md bg-(--ui-bg-quaternary) px-2 py-1 text-xs" onClick={onResume}>Resume</button>}
      </div>
    </div>
  )
}
