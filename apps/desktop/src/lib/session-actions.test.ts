import { describe, expect, it, vi } from 'vitest'

import { stopActiveSession } from './session-actions'

describe('stopActiveSession', () => {
  it('reports no-active-session instead of throwing when idle', async () => {
    const request = vi.fn()

    expect(await stopActiveSession(request, null)).toEqual({
      stopped: false,
      reason: 'no-active-session',
    })
    expect(await stopActiveSession(request, '')).toEqual({
      stopped: false,
      reason: 'no-active-session',
    })
    expect(request).not.toHaveBeenCalled()
  })

  it('interrupts the active session through the real gateway method', async () => {
    const request = vi.fn(async (): Promise<any> => ({}))

    const outcome = await stopActiveSession(request, 'sess-1')

    expect(outcome).toEqual({ stopped: true, sessionId: 'sess-1' })
    expect(request).toHaveBeenCalledWith('session.interrupt', { session_id: 'sess-1' })
  })

  it('lets gateway failures propagate for honest reporting', async () => {
    const request = vi.fn(async (): Promise<any> => {
      throw new Error('gateway offline')
    })

    await expect(stopActiveSession(request, 'sess-1')).rejects.toThrow('gateway offline')
  })
})
