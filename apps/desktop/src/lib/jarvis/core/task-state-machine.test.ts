import { describe, expect, it } from 'vitest'

import {
  canTransition,
  classifyError,
  createTask,
  transition
} from '@/lib/jarvis/core/task-state-machine'

describe('jarvis task state machine', () => {
  it('creates queued tasks', () => {
    const t = createTask({ raw: 'open chrome', inputType: 'text' })
    expect(t.status).toBe('queued')
    expect(t.id).toMatch(/^jt_/)
  })

  it('allows the happy-path chain', () => {
    const t = createTask({ raw: 'x', inputType: 'text' })
    for (const s of ['understanding', 'planning', 'executing', 'waiting_tool', 'observing', 'completed'] as const) {
      transition(t, s)
    }
    expect(t.status).toBe('completed')
    expect(t.completedAt).toBeDefined()
  })

  it('allows executing → recovering → executing', () => {
    const t = createTask({ raw: 'x', inputType: 'text' })
    transition(t, 'understanding')
    transition(t, 'planning')
    transition(t, 'executing')
    transition(t, 'recovering')
    transition(t, 'executing')
    expect(t.status).toBe('executing')
  })

  it('rejects invalid transitions', () => {
    const t = createTask({ raw: 'x', inputType: 'text' })
    expect(() => transition(t, 'completed')).toThrow(/Invalid task transition/)
    expect(canTransition('queued', 'completed')).toBe(false)
  })

  it('classifies errors honestly', () => {
    expect(classifyError('Gateway is not connected').kind).toBe('retryable')
    expect(classifyError('Blocked by permission policy').kind).toBe('permission_denied')
    expect(classifyError('Which file did you mean?').kind).toBe('requires_user_input')
    expect(classifyError('invalid argument: foo').kind).toBe('fatal')
  })
})
