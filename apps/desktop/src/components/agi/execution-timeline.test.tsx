import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import type { SubagentNode } from '@/store/subagents'

import { ExecutionTimeline, nodeTimelineEvents } from './execution-timeline'

afterEach(() => cleanup())

const node = (overrides: Partial<SubagentNode> = {}): SubagentNode => ({
  children: [],
  filesRead: [],
  filesWritten: [],
  goal: 'goal',
  id: `n-${Math.random().toString(36).slice(2)}`,
  parentId: null,
  startedAt: 1_700_000_000_000,
  status: 'running',
  stream: [],
  taskCount: 1,
  taskIndex: 0,
  updatedAt: 1_700_000_000_000,
  ...overrides,
})

describe('nodeTimelineEvents', () => {
  it('emits started + terminal events in time order', () => {
    const events = nodeTimelineEvents([
      node({ id: 'a', goal: 'Research', status: 'completed', startedAt: 1000, updatedAt: 3000, summary: 'Done' }),
      node({ id: 'b', goal: 'Code', status: 'running', startedAt: 2000, updatedAt: 2000 }),
    ])

    expect(events.map(e => e.id)).toEqual(['a:started', 'b:started', 'a:terminal'])
    expect(events[2]?.tone).toBe('good')
    expect(events[2]?.label).toContain('Done')
  })

  it('drops events without timestamps instead of guessing', () => {
    expect(nodeTimelineEvents([node({ startedAt: 0, updatedAt: 0, status: 'completed' })])).toEqual([])
    expect(nodeTimelineEvents([])).toEqual([])
  })

  it('marks failure and cancellation honestly', () => {
    const events = nodeTimelineEvents([
      node({ id: 'f', status: 'failed', startedAt: 1000, updatedAt: 2000 }),
      node({ id: 'c', status: 'interrupted', startedAt: 1000, updatedAt: 2000 }),
    ])

    expect(events.find(e => e.id === 'f:terminal')?.tone).toBe('bad')
    expect(events.find(e => e.id === 'c:terminal')?.label).toContain('Cancelled')
  })
})

describe('ExecutionTimeline', () => {
  it('renders nothing without events', () => {
    const { container } = render(<ExecutionTimeline nodes={[]} />)
    expect(container.querySelector('[data-testid="execution-timeline"]')).toBeNull()
  })

  it('renders the operational history', () => {
    render(<ExecutionTimeline nodes={[node({ id: 'a', goal: 'Research', status: 'completed' })]} />)
    expect(screen.getByLabelText('Execution timeline')).toBeTruthy()
    expect(screen.getByText(/Started — Research/)).toBeTruthy()
    expect(screen.getByText(/Completed/)).toBeTruthy()
  })
})
