import { describe, expect, it, vi } from 'vitest'

import { executeLocal, resolveRoute } from '@/lib/jarvis/os/local-executor'
import type { LocalExecDeps } from '@/lib/jarvis/os/local-executor'

vi.mock('@/hermes', () => ({
  getGlobalModelInfo: async () => ({ provider: 'acme', model: 'm1' }),
  getGlobalModelOptions: async () => ({ providers: [{ slug: 'acme' }, { slug: 'other' }] }),
  setGlobalModel: async (provider: string, model: string) => ({ ok: true, provider, model })
}))

function deps(overrides: Partial<LocalExecDeps> = {}): LocalExecDeps {
  return {
    openExternal: vi.fn(async () => undefined),
    copyText: vi.fn(async () => undefined),
    notify: vi.fn(),
    navigate: vi.fn(),
    getSystemStats: vi.fn(async () => ({ cpu: 25, memory: { used: 2 * 1024 ** 3, total: 8 * 1024 ** 3, percent: 25 }, uptime: 120 })),
    screenshot: vi.fn(async () => 'data:image/png;base64,AAA'),
    ...overrides
  }
}

describe('local executor', () => {
  it('resolves known routes and rejects unknown ones', () => {
    expect(resolveRoute('memory')).toBe('/memory')
    expect(resolveRoute('/custom')).toBe('/custom')
    expect(resolveRoute('home')).toBe('/')
    expect(resolveRoute('narnia')).toBeNull()
  })

  it('navigates the app', async () => {
    const d = deps()
    const res = await executeLocal('system.navigate', { route: '/memory' }, d)
    expect(d.navigate).toHaveBeenCalledWith('/memory')
    expect(res).toMatch(/\/memory/)
    await expect(executeLocal('system.navigate', { route: 'narnia' }, d)).rejects.toThrow(/unknown destination/i)
  })

  it('reports live system stats', async () => {
    const res = await executeLocal('system.status', {}, deps())
    expect(res).toMatch(/CPU 25%/)
    expect(res).toMatch(/2\.0\/8\.0 GB/)
  })

  it('copies text and notifies', async () => {
    const d = deps()
    await executeLocal('os.clipboard-write', { text: 'hi' }, d)
    expect(d.copyText).toHaveBeenCalledWith('hi')
    await executeLocal('os.notify', { title: 'T', message: 'M' }, d)
    expect(d.notify).toHaveBeenCalledWith('T', 'M')
  })

  it('inspects and selects models through the backend', async () => {
    const info = await executeLocal('models.inspect', {}, deps())
    expect(info).toMatch(/acme\/m1/)
    const sel = await executeLocal('models.select', { provider: 'acme', model: 'm2' }, deps())
    expect(sel).toMatch(/acme\/m2/)
  })

  it('rejects unknown handlers instead of faking success', async () => {
    await expect(executeLocal('os.format-drive', {}, deps())).rejects.toThrow(/unknown local handler/i)
  })
})
