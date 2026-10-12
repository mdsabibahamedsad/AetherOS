import { afterEach, describe, expect, it } from 'vitest'

import { $activeSessionId } from '@/store/session'

import {
  $allApprovalRequests,
  $approvalRequest,
  clearAllPrompts,
  clearApprovalRequest,
  setApprovalRequest,
} from './prompts'

afterEach(() => {
  clearAllPrompts()
  $activeSessionId.set(null)
})

describe('approval prompt parking', () => {
  it('exposes every parked approval across sessions via $all', () => {
    setApprovalRequest({ command: 'rm -rf /tmp/a', description: 'd1', sessionId: 'sess-a' })
    setApprovalRequest({ command: 'sudo reboot', description: 'd2', sessionId: 'sess-b' })

    const all = $allApprovalRequests.get()
    expect(Object.keys(all).sort()).toEqual(['sess-a', 'sess-b'])
    expect(all['sess-a']?.command).toBe('rm -rf /tmp/a')
  })

  it('scopes the active view to the foreground session only', () => {
    setApprovalRequest({ command: 'cmd-a', description: 'd', sessionId: 'sess-a' })
    setApprovalRequest({ command: 'cmd-b', description: 'd', sessionId: 'sess-b' })
    $activeSessionId.set('sess-b')

    expect($approvalRequest.get()?.command).toBe('cmd-b')
    // Background prompt still parked and visible to center views.
    expect($allApprovalRequests.get()['sess-a']?.command).toBe('cmd-a')
  })

  it('clearing one session leaves the other parked', () => {
    setApprovalRequest({ command: 'cmd-a', description: 'd', sessionId: 'sess-a' })
    setApprovalRequest({ command: 'cmd-b', description: 'd', sessionId: 'sess-b' })
    clearApprovalRequest('sess-a')

    expect($allApprovalRequests.get()['sess-a']).toBeUndefined()
    expect($allApprovalRequests.get()['sess-b']?.command).toBe('cmd-b')
  })
})
