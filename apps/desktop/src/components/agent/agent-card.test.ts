import { describe, expect, it } from 'vitest'

import type { SubagentNode } from '@/store/subagents'

import { summarizeAgentNodes } from './agent-card'

const node = (overrides: Partial<SubagentNode> = {}): SubagentNode => ({
  children: [],
  filesRead: [],
  filesWritten: [],
  goal: 'goal',
  id: `n-${Math.random().toString(36).slice(2)}`,
  parentId: null,
  startedAt: 1,
  status: 'running',
  stream: [],
  taskCount: 1,
  taskIndex: 0,
  updatedAt: 2,
  ...overrides,
})

describe('summarizeAgentNodes', () => {
  it('counts terminal nodes as done across the whole tree', () => {
    const nodes = [
      node({ status: 'completed', inputTokens: 100, outputTokens: 50, filesWritten: ['a.ts'] }),
      node({
        status: 'running',
        currentTool: 'browser_navigate',
        model: 'm1',
        children: [node({ status: 'failed' }), node({ status: 'queued' })],
      }),
    ]

    const summary = summarizeAgentNodes(nodes)

    expect(summary.total).toBe(4)
    expect(summary.completed).toBe(2)
    expect(summary.currentTool).toBe('browser_navigate')
    expect(summary.models).toEqual(['m1'])
    expect(summary.tokens).toBe(150)
    expect(summary.filesChanged).toBe(1)
  })

  it('returns honest zeros for an empty tree', () => {
    expect(summarizeAgentNodes([])).toEqual({
      completed: 0,
      currentTool: null,
      filesChanged: 0,
      models: [],
      tokens: 0,
      total: 0,
    })
  })

  it('ignores blank model names', () => {
    const summary = summarizeAgentNodes([node({ model: '' }), node({ model: 'm2' })])
    expect(summary.models).toEqual(['m2'])
  })
})
