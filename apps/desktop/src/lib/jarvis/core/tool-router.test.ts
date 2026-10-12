import { describe, expect, it } from 'vitest'

import { getCapability } from '@/lib/jarvis/capabilities/registry'
import { DEFAULT_POLICY } from '@/lib/jarvis/permissions/policy'
import { routeCommand, validateToolCall } from '@/lib/jarvis/core/tool-router'

const CTX = {
  policy: DEFAULT_POLICY,
  sessionGrants: new Set<never>(),
  gatewayOpen: true,
  localHandlers: new Set([
    'os.launch-app', 'os.open-url', 'os.clipboard-write', 'os.screenshot',
    'os.notify', 'models.inspect', 'models.select', 'system.status', 'system.navigate'
  ]),
  inputType: 'text' as const
}

describe('jarvis tool router', () => {
  it('routes "open chrome" to computer.launch-app', () => {
    const r = routeCommand('Open Chrome')
    expect('code' in r).toBe(false)
    if (!('code' in r)) {
      expect(r.capability.id).toBe('computer.launch-app')
      expect(r.input.appId).toBe('chrome')
    }
  })

  it('routes text and voice identically (parity)', () => {
    const a = routeCommand('open chrome')
    const b = routeCommand('OPEN CHROME')
    expect(JSON.stringify(a)).toBe(JSON.stringify(b))
  })

  it('validates missing args', () => {
    const v = validateToolCall('files.read', {}, CTX)
    expect(v).toMatchObject({ code: 'INVALID_ARGS' })
  })

  it('rejects unknown tools', () => {
    const v = validateToolCall('nope.tool', {}, CTX)
    expect(v).toMatchObject({ code: 'UNKNOWN_TOOL' })
  })

  it('reports gateway unavailability honestly', () => {
    const v = validateToolCall('browser.search-web', { query: 'x' }, { ...CTX, gatewayOpen: false })
    expect(v).toMatchObject({ code: 'UNAVAILABLE' })
  })

  it('denies when policy denies', () => {
    const v = validateToolCall('files.delete', { paths: 'a' }, {
      ...CTX,
      policy: { ...DEFAULT_POLICY, destructive: 'deny' }
    })
    expect(v).toMatchObject({ code: 'DENIED' })
  })

  it('new computer capabilities exist', () => {
    expect(getCapability('computer.window')).not.toBeNull()
    expect(getCapability('computer.input')).not.toBeNull()
  })
})
