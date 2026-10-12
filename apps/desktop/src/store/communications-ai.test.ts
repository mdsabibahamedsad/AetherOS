import { beforeEach, describe, expect, it } from 'vitest'

import type { UnifiedMessage } from './communications'
import {
  $commsAI, addHistory, classifyPriority, clearAssistantHistory,
  detectPendingRequests, extractTasks, generateDraft,
  generateSummary, setAssistantMode, setDraftStyle,
} from './communications-ai'

describe('communications-ai store', () => {
  beforeEach(() => {
    $commsAI.set({
      mode: 'suggest',
      draftResult: null,
      currentSummary: null,
      suggestions: [],
      selectedStyle: 'professional',
      customInstructions: '',
      targetLanguage: '',
      loading: false,
      history: [],
    })
  })

  it('generates a draft', () => {
    const messages: UnifiedMessage[] = [{
      id: '1', platform: 'telegram', conversationId: 'c1', senderId: 's1',
      senderName: 'Alice', content: 'Can you help me with this?', timestamp: new Date().toISOString(),
      direction: 'incoming', status: 'sent', read: false, pinned: false,
      archived: false, important: false, aiReplied: false, aiResponse: null,
      attachments: [],
    }]

    generateDraft(messages, 'professional')
    const draft = $commsAI.get().draftResult
    expect(draft).not.toBeNull()
    expect(draft!.requiresApproval).toBe(true)
    expect(draft!.style).toBe('professional')
  })

  it('generates a casual draft', () => {
    const messages: UnifiedMessage[] = [{
      id: '1', platform: 'telegram', conversationId: 'c1', senderId: 's1',
      senderName: 'Bob', content: 'See you tomorrow!', timestamp: new Date().toISOString(),
      direction: 'incoming', status: 'sent', read: false, pinned: false,
      archived: false, important: false, aiReplied: false, aiResponse: null,
      attachments: [],
    }]

    generateDraft(messages, 'casual')
    expect($commsAI.get().draftResult?.content).toContain('Hey')
  })

  it('generates summary', () => {
    const messages: UnifiedMessage[] = [
      { id: '1', platform: 'telegram', conversationId: 'c1', senderId: 's1', senderName: 'Alice', content: 'Hello', timestamp: new Date().toISOString(), direction: 'incoming', status: 'sent', read: false, pinned: false, archived: false, important: false, aiReplied: false, aiResponse: null, attachments: [] },
      { id: '2', platform: 'telegram', conversationId: 'c1', senderId: 's2', senderName: 'Bob', content: 'Hi there! Important update', timestamp: new Date().toISOString(), direction: 'incoming', status: 'sent', read: false, pinned: false, archived: false, important: false, aiReplied: false, aiResponse: null, attachments: [] },
    ]

    generateSummary(messages)
    const summary = $commsAI.get().currentSummary
    expect(summary).not.toBeNull()
    expect(summary!.messageCount).toBe(2)
    expect(summary!.participants).toContain('Alice')
  })

  it('classifies priority', () => {
    const messages: UnifiedMessage[] = [
      { id: '1', platform: 'telegram', conversationId: 'c1', senderId: 's1', senderName: 'Urgent Sender', content: 'This is urgent! Need help ASAP', timestamp: new Date().toISOString(), direction: 'incoming', status: 'sent', read: false, pinned: false, archived: false, important: false, aiReplied: false, aiResponse: null, attachments: [] },
      { id: '2', platform: 'telegram', conversationId: 'c2', senderId: 's2', senderName: 'Spam Sender', content: 'Free money!!! Click here', timestamp: new Date().toISOString(), direction: 'incoming', status: 'sent', read: false, pinned: false, archived: false, important: false, aiReplied: false, aiResponse: null, attachments: [] },
      { id: '3', platform: 'telegram', conversationId: 'c3', senderId: 's3', senderName: 'Normal', content: 'Just checking in', timestamp: new Date().toISOString(), direction: 'incoming', status: 'sent', read: false, pinned: false, archived: false, important: false, aiReplied: false, aiResponse: null, attachments: [] },
    ]

    const result = classifyPriority(messages)
    expect(result.urgent).toHaveLength(1)
    expect(result.spam).toHaveLength(1)
    expect(result.normal).toHaveLength(1)
  })

  it('extracts tasks from messages', () => {
    const messages: UnifiedMessage[] = [
      { id: '1', platform: 'telegram', conversationId: 'c1', senderId: 's1', senderName: 'Manager', content: 'I will review the PR by Friday', timestamp: new Date().toISOString(), direction: 'incoming', status: 'sent', read: false, pinned: false, archived: false, important: false, aiReplied: false, aiResponse: null, attachments: [] },
      { id: '2', platform: 'telegram', conversationId: 'c1', senderId: 's1', senderName: 'Manager', content: 'Please update the documentation', timestamp: new Date().toISOString(), direction: 'incoming', status: 'sent', read: false, pinned: false, archived: false, important: false, aiReplied: false, aiResponse: null, attachments: [] },
    ]

    const tasks = extractTasks(messages)
    expect(tasks.length).toBeGreaterThanOrEqual(1)
    expect(tasks.some(t => t.task.toLowerCase().includes('update'))).toBe(true)
  })

  it('detects pending requests', () => {
    const messages: UnifiedMessage[] = [
      { id: '1', platform: 'telegram', conversationId: 'c1', senderId: 's1', senderName: 'Alice', content: 'Can you send me the report?', timestamp: new Date().toISOString(), direction: 'incoming', status: 'sent', read: false, pinned: false, archived: false, important: false, aiReplied: false, aiResponse: null, attachments: [] },
      { id: '2', platform: 'telegram', conversationId: 'c1', senderId: 's1', senderName: 'Alice', content: 'Please review my pull request', timestamp: new Date().toISOString(), direction: 'incoming', status: 'sent', read: false, pinned: false, archived: false, important: false, aiReplied: false, aiResponse: null, attachments: [] },
    ]

    const pending = detectPendingRequests(messages)
    expect(pending.length).toBeGreaterThanOrEqual(2)
  })

  it('adds and clears history', () => {
    addHistory('user', 'Draft a reply')
    addHistory('assistant', 'Here is a draft')
    expect($commsAI.get().history).toHaveLength(2)
    clearAssistantHistory()
    expect($commsAI.get().history).toHaveLength(0)
    expect($commsAI.get().draftResult).toBeNull()
  })

  it('sets assistant mode', () => {
    setAssistantMode('draft')
    expect($commsAI.get().mode).toBe('draft')
  })

  it('sets draft style', () => {
    setDraftStyle('friendly')
    expect($commsAI.get().selectedStyle).toBe('friendly')
  })
})
