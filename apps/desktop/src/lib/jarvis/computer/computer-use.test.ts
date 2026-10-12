import { describe, expect, it, vi } from 'vitest'

import {
  click,
  describeScreen,
  launchApplication,
  typeText
} from '@/lib/jarvis/computer/computer-use'

const DEPS = {
  launchApp: vi.fn(async (id: string) => `Opened ${id}.`),
  openUrl: vi.fn(async (url: string) => `Opened ${url}.`),
  screenshot: vi.fn(async () => 'data:image/png;base64,AAA'),
  gatewayOpen: false
}

describe('jarvis computer use', () => {
  it('launches allowlisted apps and verifies with observation', async () => {
    const r = await launchApplication(DEPS, 'chrome')
    expect(r.success).toBe(true)
    expect(r.observation).toMatch(/Opened chrome/)
  })

  it('rejects invalid app ids without touching the OS', async () => {
    const r = await launchApplication(DEPS, 'C:\\Windows\\evil.exe')
    expect(r.success).toBe(false)
    expect(DEPS.launchApp).not.toHaveBeenCalledWith('C:\\Windows\\evil.exe')
  })

  it('rejects blind coordinates', async () => {
    const r = await click(DEPS, { x: 100, y: 200 })
    expect(r.success).toBe(false)
    expect(r.error).toMatch(/observation-verified/i)
  })

  it('routes validated pointer actions to the gateway, honestly offline', async () => {
    const r = await click(DEPS, { label: 'Download button', fromObservation: true })
    expect(r.success).toBe(false)
    expect(r.error).toMatch(/gateway/i)
  })

  it('describes the screen from a real capture even when offline', async () => {
    const r = await describeScreen(DEPS, 'screen')
    expect(r.success).toBe(true)
    expect(r.observation).toMatch(/Vision analysis needs the gateway/)
  })

  it('bounds typed text', async () => {
    const r = await typeText(DEPS, '')
    expect(r.success).toBe(false)
  })
})
