import { describe, expect, it } from 'vitest'

import { CAPABILITY_LABEL, describeToolset, RISK_LABEL, toolsetProfile } from './tool-registry'

const info = (overrides = {}) => ({
  configured: true,
  description: '',
  enabled: true,
  label: 'Terminal',
  name: 'terminal',
  tools: ['run', 'kill'],
  ...overrides,
})

describe('toolsetProfile', () => {
  it('profiles known executors as high-risk sandboxed', () => {
    expect(toolsetProfile('terminal')).toMatchObject({
      capabilities: ['execute', 'system'],
      risk: 'high',
    })
    expect(toolsetProfile('execute_code').environments).toContain('sandbox')
  })

  it('keeps reads low-risk and messaging high-risk', () => {
    expect(toolsetProfile('search').risk).toBe('low')
    expect(toolsetProfile('messaging').risk).toBe('high')
    expect(toolsetProfile('admin').risk).toBe('destructive')
  })

  it('falls back cautiously for unclassified toolsets', () => {
    const profile = toolsetProfile('something-new')
    expect(profile.risk).toBe('medium')
    expect(profile.capabilities).toEqual([])
  })
})

describe('describeToolset', () => {
  it('joins live state with advisory metadata', () => {
    const view = describeToolset(info({ enabled: false }))
    expect(view).toMatchObject({
      name: 'terminal',
      label: 'Terminal',
      enabled: false,
      configured: true,
      risk: 'high',
      toolCount: 2,
    })
  })

  it('handles missing labels and tool lists', () => {
    const view = describeToolset(info({ label: '', tools: null }))
    expect(view.label).toBe('terminal')
    expect(view.toolCount).toBe(0)
  })

  it('labels every capability and risk tier', () => {
    expect(Object.keys(CAPABILITY_LABEL)).toHaveLength(9)
    expect(RISK_LABEL.destructive).toBe('Destructive')
  })
})
