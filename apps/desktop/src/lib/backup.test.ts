import { describe, expect, it, vi } from 'vitest'

import { pollActionDone } from './backup'

const status = (overrides = {}) => ({
  exit_code: null,
  lines: [],
  name: 'backup',
  pid: 123,
  running: true,
  ...overrides,
})

describe('pollActionDone', () => {
  it('resolves success from a real zero exit code', async () => {
    const getStatus = vi.fn(async () => status({ running: false, exit_code: 0, lines: ['done'] }))

    await expect(pollActionDone(getStatus, 'backup', { intervalMs: 1 })).resolves.toEqual({
      lines: ['done'],
      ok: true,
    })
    expect(getStatus).toHaveBeenCalledWith('backup', 20)
  })

  it('waits while running, then reports a real failure', async () => {
    const getStatus = vi
      .fn(async () => status())
      .mockResolvedValueOnce(status())
      .mockResolvedValueOnce(status({ running: false, exit_code: 1, lines: ['boom'] }))

    await expect(pollActionDone(getStatus, 'backup', { intervalMs: 1 })).resolves.toEqual({
      lines: ['boom'],
      ok: false,
    })
    expect(getStatus.mock.calls.length).toBeGreaterThanOrEqual(2)
  })

  it('throws on timeout instead of faking completion', async () => {
    const getStatus = vi.fn(async () => status())

    await expect(pollActionDone(getStatus, 'backup', { intervalMs: 1, timeoutMs: 5 })).rejects.toThrow(
      'timed out',
    )
  })
})
