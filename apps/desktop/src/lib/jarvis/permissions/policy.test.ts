import { describe, expect, it } from 'vitest'

import type { Capability } from '@/lib/jarvis/capabilities/registry'
import { decideCapability, DEFAULT_POLICY, looksDestructive, sanitizePolicy } from '@/lib/jarvis/permissions/policy'

function cap(overrides: Partial<Capability>): Capability {
  return {
    id: 'test.cap',
    name: 'Test',
    description: 'Test capability',
    category: 'system',
    inputSchema: { type: 'object', properties: {}, required: [] },
    outputSchema: { type: 'object', properties: {}, required: [] },
    permissions: [],
    riskLevel: 'low',
    supportsStreaming: false,
    supportsCancellation: false,
    supportsApproval: false,
    binding: { via: 'local', handler: 'test' },
    ...overrides
  }
}

describe('permission policy', () => {
  it('allows permissionless capabilities', () => {
    expect(decideCapability(cap({}), { policy: DEFAULT_POLICY, sessionGrants: new Set(), inputType: 'text' }))
      .toEqual({ decision: 'allow', permission: null })
  })

  it('asks for write/execute by default', () => {
    const c = cap({ permissions: ['execute'] })
    expect(decideCapability(c, { policy: DEFAULT_POLICY, sessionGrants: new Set(), inputType: 'text' }).decision).toBe('ask')
  })

  it('honors session grants', () => {
    const c = cap({ permissions: ['execute'] })
    const policy = { ...DEFAULT_POLICY, execute: 'allow-session' as const }
    const ctx = { policy, sessionGrants: new Set(['execute' as const]), inputType: 'text' as const }
    expect(decideCapability(c, ctx).decision).toBe('allow')
  })

  it('deny always wins', () => {
    const c = cap({ permissions: ['read', 'execute'] })
    const policy = { ...DEFAULT_POLICY, execute: 'deny' as const }
    const res = decideCapability(c, { policy, sessionGrants: new Set(), inputType: 'text' })
    expect(res).toEqual({ decision: 'deny', permission: 'execute' })
  })

  it('destructive and communicate can never be always-allow', () => {
    const clean = sanitizePolicy({ destructive: 'always-allow', communicate: 'always-allow' })
    expect(clean.destructive).toBe('ask')
    expect(clean.communicate).toBe('ask')
  })

  it('voice follows the identical approval rule as text', () => {
    const c = cap({ permissions: ['destructive'], riskLevel: 'critical' })

    for (const inputType of ['text', 'voice'] as const) {
      const res = decideCapability(c, { policy: DEFAULT_POLICY, sessionGrants: new Set(), inputType })
      expect(res.decision).toBe('ask')
    }
  })

  it('detects destructive phrasing', () => {
    expect(looksDestructive('delete all 24 files')).toBe(true)
    expect(looksDestructive('rm -rf /tmp/cache')).toBe(true)
    expect(looksDestructive('send an email to the team')).toBe(true)
    expect(looksDestructive('show me the release report')).toBe(false)
  })
})
