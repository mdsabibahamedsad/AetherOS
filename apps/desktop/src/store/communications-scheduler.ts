import { atom } from 'nanostores'

export type ScheduleRecurrence = 'none' | 'daily' | 'weekly' | 'monthly' | 'weekdays' | 'custom'
export type ScheduledMessageStatus = 'pending' | 'scheduled' | 'sent' | 'failed' | 'cancelled' | 'paused'

export interface ScheduledMessage {
  id: string
  provider: string
  accountId: string
  recipientId: string
  recipientName: string
  content: string
  scheduledAt: string
  status: ScheduledMessageStatus
  recurrence: ScheduleRecurrence
  recurrenceConfig: Record<string, unknown>
  attachments: string[]
  requireApproval: boolean
  approved: boolean
  templateId: string
  parentId: string
  sentAt: string
  errorMessage: string
  createdAt: string
  createdBy: string
}

export interface SchedulerState {
  messages: ScheduledMessage[]
  viewFilter: 'upcoming' | 'all' | 'history'
  loading: boolean
}

const generateId = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`

const initialState: SchedulerState = {
  messages: [],
  viewFilter: 'upcoming',
  loading: false,
}

export const $scheduler = atom<SchedulerState>(initialState)

const patch = (update: Partial<SchedulerState>) =>
  $scheduler.set({ ...$scheduler.get(), ...update })

export function setSchedulerFilter(filter: SchedulerState['viewFilter']) { patch({ viewFilter: filter }) }

export function setSchedulerLoading(loading: boolean) { patch({ loading }) }

export function scheduleMessage(msg: Omit<ScheduledMessage, 'id' | 'createdAt'>) {
  const newMsg: ScheduledMessage = { ...msg, id: generateId(), createdAt: new Date().toISOString() }
  patch({ messages: [...$scheduler.get().messages, newMsg] })
}

export function cancelScheduledMessage(id: string) {
  const messages = $scheduler.get().messages.map(m =>
    m.id === id && (m.status === 'pending' || m.status === 'scheduled')
      ? { ...m, status: 'cancelled' as ScheduledMessageStatus }
      : m
  )

  patch({ messages })
}

export function pauseScheduledMessage(id: string) {
  const messages = $scheduler.get().messages.map(m =>
    m.id === id && m.status === 'scheduled'
      ? { ...m, status: 'paused' as ScheduledMessageStatus }
      : m
  )

  patch({ messages })
}

export function resumeScheduledMessage(id: string) {
  const messages = $scheduler.get().messages.map(m =>
    m.id === id && m.status === 'paused'
      ? { ...m, status: 'scheduled' as ScheduledMessageStatus }
      : m
  )

  patch({ messages })
}

export function rescheduleMessage(id: string, newTime: string) {
  const messages = $scheduler.get().messages.map(m =>
    m.id === id ? { ...m, scheduledAt: newTime, status: 'scheduled' as ScheduledMessageStatus } : m
  )

  patch({ messages })
}

export function updateScheduledContent(id: string, content: string) {
  const messages = $scheduler.get().messages.map(m =>
    m.id === id ? { ...m, content } : m
  )

  patch({ messages })
}

export function approveScheduledMessage(id: string) {
  const messages = $scheduler.get().messages.map(m =>
    m.id === id ? { ...m, approved: true } : m
  )

  patch({ messages })
}

export function markScheduledSent(id: string) {
  const messages = $scheduler.get().messages.map(m =>
    m.id === id ? { ...m, status: 'sent' as ScheduledMessageStatus, sentAt: new Date().toISOString() } : m
  )

  patch({ messages })
}

export function markScheduledFailed(id: string, error: string) {
  const messages = $scheduler.get().messages.map(m =>
    m.id === id ? { ...m, status: 'failed' as ScheduledMessageStatus, errorMessage: error } : m
  )

  patch({ messages })
}

export function getFilteredScheduledMessages(): ScheduledMessage[] {
  const state = $scheduler.get()
  const now = new Date()

  switch (state.viewFilter) {
    case 'upcoming':
      return state.messages
        .filter(m => m.status === 'scheduled' || m.status === 'pending')
        .sort((a, b) => new Date(a.scheduledAt).getTime() - new Date(b.scheduledAt).getTime())

    case 'history':
      return state.messages
        .filter(m => m.status === 'sent' || m.status === 'failed' || m.status === 'cancelled')
        .sort((a, b) => new Date(b.scheduledAt).getTime() - new Date(a.scheduledAt).getTime())

    default:
      return [...state.messages].sort((a, b) => new Date(a.scheduledAt).getTime() - new Date(b.scheduledAt).getTime())
  }
}
