import { describe, expect, it } from 'vitest'

import { getTaskRowActions, partitionActiveTasks, pauseResumeAction } from './index'

// A terminal status must never be double-counted in Active + Completed
// (Master 58362: `success` appeared in both partitions).
describe('partitionActiveTasks', () => {
  it('excludes every settled id from active', () => {
    const rows = [
      { id: 'a', status: 'running' },
      { id: 'b', status: 'success' },
      { id: 'c', status: 'error' },
      { id: 'd', status: 'pending' },
    ]

    const settled = new Set(['b', 'c'])

    expect(partitionActiveTasks(rows, settled).map(r => r.id)).toEqual(['a', 'd'])
  })

  it('keeps everything active when nothing settled', () => {
    const rows = [{ id: 'a', status: 'running' }]

    expect(partitionActiveTasks(rows, new Set())).toEqual(rows)
  })
})

describe('getTaskRowActions', () => {
  it('exposes the full lifecycle for live cron rows', () => {
    expect(getTaskRowActions({ status: 'pending', type: 'cron' }))
      .toEqual(['pause', 'trigger', 'view', 'delete'])
  })

  it('offers view + delete only for terminal cron rows', () => {
    for (const status of ['completed', 'cancelled', 'error', 'failed']) {
      expect(getTaskRowActions({ status, type: 'cron' })).toEqual(['view', 'delete'])
    }
  })

  it('keeps desktop-action rows view-only (no stop endpoint exists)', () => {
    for (const status of ['running', 'success', 'error']) {
      expect(getTaskRowActions({ status, type: 'action' })).toEqual(['view'])
    }
  })

  it('resolves pause vs resume from the paused flag', () => {
    expect(pauseResumeAction(false)).toBe('pause')
    expect(pauseResumeAction(true)).toBe('resume')
  })
})
