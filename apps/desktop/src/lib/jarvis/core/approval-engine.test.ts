import { describe, expect, it } from 'vitest'

import { getCapability } from '@/lib/jarvis/capabilities/registry'
import {
  decideApproval,
  levelForCapability,
  requestApproval
} from '@/lib/jarvis/core/approval-engine'

describe('jarvis approval engine', () => {
  it('maps risk to levels', () => {
    expect(levelForCapability(getCapability('system.navigate')!)).toBe('NONE')
    expect(levelForCapability(getCapability('files.delete')!)).toBe('CRITICAL')
    expect(levelForCapability(getCapability('communications.send')!)).toBe('HIGH')
  })

  it('NONE auto-passes without a ticket', async () => {
    await expect(requestApproval({
      capabilityId: 'system.navigate',
      summary: 'x',
      level: 'NONE',
      inputType: 'text'
    })).resolves.toBe(true)
  })

  it('HIGH waits for an explicit decision', async () => {
    const pending = requestApproval({
      capabilityId: 'files.delete',
      summary: 'Delete 14 files',
      level: 'HIGH',
      inputType: 'voice'
    })
    const { pendingApprovals } = await import('@/lib/jarvis/core/approval-engine')
    const tickets = pendingApprovals()
    expect(tickets.length).toBeGreaterThan(0)
    decideApproval(tickets[tickets.length - 1].id, true)
    await expect(pending).resolves.toBe(true)
  })
})
