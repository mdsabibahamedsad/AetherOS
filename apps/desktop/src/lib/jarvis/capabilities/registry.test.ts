import { describe, expect, it } from 'vitest'

import {
  CAPABILITIES,
  capabilitiesByCategory,
  capabilityForTool,
  getCapability,
  resolveAvailability
} from '@/lib/jarvis/capabilities/registry'

describe('capability registry', () => {
  it('declares a complete contract for every capability', () => {
    expect(CAPABILITIES.length).toBeGreaterThan(20)

    const ids = new Set<string>()

    for (const cap of CAPABILITIES) {
      expect(cap.id).toBeTruthy()
      expect(ids.has(cap.id)).toBe(false)
      ids.add(cap.id)
      expect(cap.name).toBeTruthy()
      expect(cap.description).toBeTruthy()
      expect(cap.category).toBeTruthy()
      expect(cap.inputSchema.type).toBe('object')
      expect(cap.outputSchema.type).toBe('object')
      expect(Array.isArray(cap.permissions)).toBe(true)
      expect(['low', 'medium', 'high', 'critical']).toContain(cap.riskLevel)
      expect(typeof cap.supportsStreaming).toBe('boolean')
      expect(typeof cap.supportsCancellation).toBe('boolean')
      expect(typeof cap.supportsApproval).toBe('boolean')
      expect(cap.binding.via).toMatch(/^(gateway-agent|local)$/)

      if (cap.binding.via === 'local') {expect(cap.binding.handler).toBeTruthy()}

      for (const req of cap.inputSchema.required) {
        expect(cap.inputSchema.properties[req]).toBeTruthy()
      }
    }
  })

  it('covers every required category', () => {
    for (const cat of ['computer', 'browser', 'terminal', 'files', 'code', 'memory', 'knowledge', 'automation', 'communications', 'agents', 'models', 'system'] as const) {
      expect(capabilitiesByCategory(cat).length).toBeGreaterThan(0)
    }
  })

  it('marks gateway capabilities unavailable when the gateway is closed', () => {
    const resolved = resolveAvailability({ gatewayOpen: false, localHandlers: new Set(['system.status']) })
    const gw = resolved.filter(r => r.binding.via === 'gateway-agent')

    expect(gw.length).toBeGreaterThan(0)

    for (const cap of gw) {
      expect(cap.available).toBe(false)
      expect(cap.unavailableReason).toMatch(/disconnected/i)
    }

    const sys = resolved.find(r => r.id === 'system.status')
    expect(sys?.available).toBe(true)
    expect(sys?.unavailableReason).toBeNull()
  })

  it('marks local capabilities unavailable when their handler is missing', () => {
    const resolved = resolveAvailability({ gatewayOpen: true, localHandlers: new Set() })
    const missing = resolved.find(r => r.id === 'computer.screenshot')

    expect(missing?.available).toBe(false)
    expect(missing?.unavailableReason).toMatch(/not registered/)
  })

  it('maps gateway tool names to capabilities for the timeline', () => {
    expect(capabilityForTool('browser_navigate')).toBe('browser.task')
    expect(capabilityForTool('terminal')).toBe('terminal.execute')
    expect(capabilityForTool('read_file')).toBe('files.read')
    expect(capabilityForTool('cronjob')).toBe('automation.schedule')
    expect(capabilityForTool('something-entirely-unknown-xyz')).toBeNull()
  })

  it('looks capabilities up by id', () => {
    expect(getCapability('terminal.execute')?.name).toBe('Execute command')
    expect(getCapability('nope')).toBeNull()
  })
})
