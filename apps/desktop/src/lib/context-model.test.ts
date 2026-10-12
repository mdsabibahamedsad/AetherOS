import { describe, expect, it } from 'vitest'

import { buildContextChain, contextSummary, scopeDescription } from './context-model'

describe('buildContextChain', () => {
  it('always starts at global and omits unknown layers', () => {
    expect(buildContextChain({})).toEqual([{ kind: 'global', label: 'AetherOS' }])
  })

  it('skips the default workspace (it is the ambient context)', () => {
    const chain = buildContextChain({ profile: 'default', appLabel: 'Home', appRoute: '/home' })
    expect(chain.map(l => l.kind)).toEqual(['global', 'app'])
  })

  it('builds the full chain with routes only where they exist', () => {
    const chain = buildContextChain({
      profile: 'coder',
      appLabel: 'Agent',
      appRoute: '/',
      sessionTitle: 'Release prep',
      sessionRoute: '/abc123',
      activeAgentCount: 2,
      currentTool: 'browser_navigate',
    })

    expect(chain.map(l => l.kind)).toEqual(['global', 'workspace', 'app', 'task', 'agent', 'action'])
    expect(chain.find(l => l.kind === 'workspace')).toMatchObject({ label: 'coder', route: '/profiles' })
    expect(chain.find(l => l.kind === 'action')).toMatchObject({ label: 'browser_navigate' })
  })

  it('omits the agent layer when nothing is active', () => {
    const chain = buildContextChain({ appLabel: 'Tasks', activeAgentCount: 0 })
    expect(chain.some(l => l.kind === 'agent')).toBe(false)
  })
})

describe('contextSummary / scopeDescription', () => {
  it('renders a compact breadcrumb without the global root', () => {
    const chain = buildContextChain({ profile: 'coder', appLabel: 'Agent', sessionTitle: 'Release prep' })
    expect(contextSummary(chain)).toBe('coder › Agent › Release prep')
  })

  it('describes intent scope honestly, preferring the deepest layer', () => {
    expect(scopeDescription(buildContextChain({}))).toBeNull()
    expect(scopeDescription(buildContextChain({ profile: 'coder' }))).toBe('Workspace coder')
    expect(
      scopeDescription(buildContextChain({ profile: 'coder', appLabel: 'Files', sessionTitle: 'Q3 report' })),
    ).toBe('Q3 report (coder)')
  })
})
