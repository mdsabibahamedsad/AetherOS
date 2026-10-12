import { describe, expect, it, vi } from 'vitest'

import { emergencyStopAll } from './emergency-stop'

describe('emergencyStopAll', () => {
  it('interrupts every live session and runs all legs, reporting per-leg results', async () => {
    const calls: Array<{ method: string; params: Record<string, unknown> }> = []

    const request = vi.fn(async (method: string, params: Record<string, unknown> = {}): Promise<any> => {
      calls.push({ method, params })

      if (method === 'session.active_list') {
        return { sessions: [{ id: 'a' }, { id: 'b' }] }
      }

      if (method === 'process.stop') {
        return { killed: 2 }
      }

      return {}
    })

    const report = await emergencyStopAll(request)

    expect(report.stoppedSessions).toBe(2)
    expect(report.legs).toHaveLength(4)
    expect(report.legs.every(l => l.ok)).toBe(true)
    expect(calls.map(c => c.method)).toContain('session.interrupt')
    expect(calls.filter(c => c.method === 'session.interrupt')).toHaveLength(2)
    expect(calls.map(c => c.method)).toEqual(
      expect.arrayContaining(['session.active_list', 'process.stop', 'automation.stop_all', 'swarm.stop']),
    )
  })

  it('surfaces partial failure per leg instead of succeeding silently', async () => {
    const request = vi.fn(async (method: string): Promise<any> => {
      if (method === 'session.active_list') {
        return { sessions: [{ id: 'a' }] }
      }

      if (method === 'session.interrupt') {
        throw new Error('nope')
      }

      if (method === 'process.stop') {
        throw new Error('down')
      }

      return {}
    })

    const report = await emergencyStopAll(request)

    expect(report.stoppedSessions).toBe(0)
    const byLeg = Object.fromEntries(report.legs.map(l => [l.leg, l]))
    expect(byLeg.sessions.ok).toBe(false)
    expect(byLeg.processes.ok).toBe(false)
    expect(byLeg.automations.ok).toBe(true)
    expect(byLeg.swarm.ok).toBe(true)
  })

  it('reports a failed session listing as its own leg', async () => {
    const request = vi.fn(async () => {
      throw new Error('gateway offline')
    })

    const report = await emergencyStopAll(request)

    expect(report.stoppedSessions).toBe(0)
    expect(report.legs[0]).toMatchObject({ leg: 'sessions', ok: false })
    expect(report.legs[0].detail).toContain('gateway offline')
  })
})
