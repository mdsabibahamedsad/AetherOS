import { beforeEach, describe, expect, it } from 'vitest'

import {
  $scheduler, approveScheduledMessage, cancelScheduledMessage, getFilteredScheduledMessages,
  markScheduledFailed, markScheduledSent, pauseScheduledMessage,
  rescheduleMessage, resumeScheduledMessage, scheduleMessage,
  setSchedulerFilter, updateScheduledContent,
} from './communications-scheduler'

describe('communications-scheduler store', () => {
  beforeEach(() => {
    $scheduler.set({
      messages: [],
      viewFilter: 'upcoming',
      loading: false,
    })
  })

  it('schedules a message', () => {
    scheduleMessage({
      provider: 'telegram', accountId: '', recipientId: '@john',
      recipientName: 'John', content: 'Hello!', scheduledAt: '2026-07-22T10:00:00',
      status: 'scheduled', recurrence: 'none', recurrenceConfig: {},
      attachments: [], requireApproval: true, approved: false,
      templateId: '', parentId: '', sentAt: '', errorMessage: '', createdBy: 'user',
    })
    expect($scheduler.get().messages).toHaveLength(1)
    expect($scheduler.get().messages[0].provider).toBe('telegram')
  })

  it('cancels a scheduled message', () => {
    scheduleMessage({ provider: 'telegram', accountId: '', recipientId: '@j', recipientName: 'J', content: 'Hi', scheduledAt: '2026-07-22T10:00:00', status: 'scheduled', recurrence: 'none', recurrenceConfig: {}, attachments: [], requireApproval: false, approved: true, templateId: '', parentId: '', sentAt: '', errorMessage: '', createdBy: 'user' })
    const id = $scheduler.get().messages[0].id
    cancelScheduledMessage(id)
    expect($scheduler.get().messages[0].status).toBe('cancelled')
  })

  it('pauses and resumes a scheduled message', () => {
    scheduleMessage({ provider: 'telegram', accountId: '', recipientId: '@j', recipientName: 'J', content: 'Hi', scheduledAt: '2026-07-22T10:00:00', status: 'scheduled', recurrence: 'none', recurrenceConfig: {}, attachments: [], requireApproval: false, approved: true, templateId: '', parentId: '', sentAt: '', errorMessage: '', createdBy: 'user' })
    const id = $scheduler.get().messages[0].id
    pauseScheduledMessage(id)
    expect($scheduler.get().messages[0].status).toBe('paused')
    resumeScheduledMessage(id)
    expect($scheduler.get().messages[0].status).toBe('scheduled')
  })

  it('reschedules a message', () => {
    scheduleMessage({ provider: 'telegram', accountId: '', recipientId: '@j', recipientName: 'J', content: 'Hi', scheduledAt: '2026-07-22T10:00:00', status: 'scheduled', recurrence: 'none', recurrenceConfig: {}, attachments: [], requireApproval: false, approved: true, templateId: '', parentId: '', sentAt: '', errorMessage: '', createdBy: 'user' })
    const id = $scheduler.get().messages[0].id
    rescheduleMessage(id, '2026-07-23T14:00:00')
    expect($scheduler.get().messages[0].scheduledAt).toBe('2026-07-23T14:00:00')
  })

  it('updates content', () => {
    scheduleMessage({ provider: 'telegram', accountId: '', recipientId: '@j', recipientName: 'J', content: 'Hi', scheduledAt: '2026-07-22T10:00:00', status: 'scheduled', recurrence: 'none', recurrenceConfig: {}, attachments: [], requireApproval: false, approved: true, templateId: '', parentId: '', sentAt: '', errorMessage: '', createdBy: 'user' })
    const id = $scheduler.get().messages[0].id
    updateScheduledContent(id, 'Updated content')
    expect($scheduler.get().messages[0].content).toBe('Updated content')
  })

  it('approves a message', () => {
    scheduleMessage({ provider: 'telegram', accountId: '', recipientId: '@j', recipientName: 'J', content: 'Hi', scheduledAt: '2026-07-22T10:00:00', status: 'scheduled', recurrence: 'none', recurrenceConfig: {}, attachments: [], requireApproval: true, approved: false, templateId: '', parentId: '', sentAt: '', errorMessage: '', createdBy: 'user' })
    const id = $scheduler.get().messages[0].id
    approveScheduledMessage(id)
    expect($scheduler.get().messages[0].approved).toBe(true)
  })

  it('marks as sent', () => {
    scheduleMessage({ provider: 'telegram', accountId: '', recipientId: '@j', recipientName: 'J', content: 'Hi', scheduledAt: '2026-07-22T10:00:00', status: 'scheduled', recurrence: 'none', recurrenceConfig: {}, attachments: [], requireApproval: false, approved: true, templateId: '', parentId: '', sentAt: '', errorMessage: '', createdBy: 'user' })
    const id = $scheduler.get().messages[0].id
    markScheduledSent(id)
    expect($scheduler.get().messages[0].status).toBe('sent')
    expect($scheduler.get().messages[0].sentAt).toBeTruthy()
  })

  it('marks as failed', () => {
    scheduleMessage({ provider: 'telegram', accountId: '', recipientId: '@j', recipientName: 'J', content: 'Hi', scheduledAt: '2026-07-22T10:00:00', status: 'scheduled', recurrence: 'none', recurrenceConfig: {}, attachments: [], requireApproval: false, approved: true, templateId: '', parentId: '', sentAt: '', errorMessage: '', createdBy: 'user' })
    const id = $scheduler.get().messages[0].id
    markScheduledFailed(id, 'Network error')
    expect($scheduler.get().messages[0].status).toBe('failed')
    expect($scheduler.get().messages[0].errorMessage).toBe('Network error')
  })

  it('filters upcoming messages', () => {
    scheduleMessage({ provider: 'telegram', accountId: '', recipientId: '@a', recipientName: 'A', content: 'Future msg', scheduledAt: '2099-01-01T10:00:00', status: 'scheduled', recurrence: 'none', recurrenceConfig: {}, attachments: [], requireApproval: false, approved: true, templateId: '', parentId: '', sentAt: '', errorMessage: '', createdBy: 'user' })
    setSchedulerFilter('history')
    expect(getFilteredScheduledMessages()).toHaveLength(0)
    setSchedulerFilter('upcoming')
    expect(getFilteredScheduledMessages()).toHaveLength(1)
  })
})
