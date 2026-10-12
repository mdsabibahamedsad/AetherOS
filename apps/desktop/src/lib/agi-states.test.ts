import { describe, expect, it } from 'vitest'

import {
  AGENT_LIFECYCLE_LABEL,
  agentLifecycleFromSubagent,
  autonomyFromYolo,
  confirmationForTier,
  TASK_STATE_LABEL,
  taskStateFromAction,
  taskStateFromCron,
} from './agi-states'

describe('agentLifecycleFromSubagent', () => {
  it('maps every runtime status without inventing states', () => {
    expect(agentLifecycleFromSubagent('running')).toBe('running')
    expect(agentLifecycleFromSubagent('queued')).toBe('waiting')
    expect(agentLifecycleFromSubagent('completed')).toBe('completed')
    expect(agentLifecycleFromSubagent('failed')).toBe('failed')
    // Interrupt halts execution: honest label is cancelled, never "paused"
    // (sessions have no backend pause state).
    expect(agentLifecycleFromSubagent('interrupted')).toBe('cancelled')
  })

  it('labels every lifecycle state', () => {
    for (const [key, label] of Object.entries(AGENT_LIFECYCLE_LABEL)) {
      expect(typeof label).toBe('string')
      expect(label.length).toBeGreaterThan(0)
      expect(key).not.toContain('thinking')
    }
  })
})

describe('task states', () => {
  it('maps cron signals: error > paused > queued', () => {
    expect(taskStateFromCron({ lastError: 'boom' })).toBe('failed')
    expect(taskStateFromCron({ paused: true })).toBe('paused')
    expect(taskStateFromCron({ enabled: false })).toBe('paused')
    expect(taskStateFromCron({})).toBe('queued')
  })

  it('maps action signals without guessing', () => {
    expect(taskStateFromAction({ running: true })).toBe('running')
    expect(taskStateFromAction({ exitCode: 0 })).toBe('completed')
    expect(taskStateFromAction({ exitCode: 1 })).toBe('failed')
    expect(taskStateFromAction({})).toBe('unknown')
  })

  it('labels every task state', () => {
    expect(Object.keys(TASK_STATE_LABEL)).toHaveLength(12)
  })
})

describe('autonomy + confirmation', () => {
  it('only claims levels backed by real YOLO controls', () => {
    expect(autonomyFromYolo({ sessionYolo: false, globalYolo: false })).toBe('supervised')
    expect(autonomyFromYolo({ sessionYolo: true, globalYolo: false })).toBe('autonomous')
    expect(autonomyFromYolo({ sessionYolo: false, globalYolo: true })).toBe('autonomous')
  })

  it('escalates confirmation with risk, never inverts', () => {
    expect(confirmationForTier('low')).toBe('none')
    expect(confirmationForTier('medium')).toBe('inline')
    expect(confirmationForTier('high')).toBe('explicit')
    expect(confirmationForTier('destructive')).toBe('strong')
  })
})
