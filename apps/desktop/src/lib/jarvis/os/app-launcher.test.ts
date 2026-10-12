import { describe, expect, it, vi } from 'vitest'

import { launchApp, listAllowedApps, openValidatedUrl, resolveApp, validateOpenUrl } from '@/lib/jarvis/os/app-launcher'

describe('app launcher allowlist', () => {
  it('resolves known apps case-insensitively', () => {
    expect(resolveApp('Chrome')?.name).toBe('Google Chrome')
    expect(resolveApp('vscode')?.name).toBe('VS Code')
  })

  it('rejects anything not allowlisted', async () => {
    const openExternal = vi.fn(async () => undefined)
    await expect(launchApp('C:\\Windows\\System32\\cmd.exe', { openExternal })).rejects.toThrow(/not an allowlisted application/)
    await expect(launchApp('evil-app', { openExternal })).rejects.toThrow(/not an allowlisted application/)
    expect(openExternal).not.toHaveBeenCalled()
  })

  it('launches allowlisted apps through openExternal only', async () => {
    const openExternal = vi.fn(async () => undefined)
    const app = await launchApp('youtube', { openExternal })
    expect(app.id).toBe('youtube')
    expect(openExternal).toHaveBeenCalledWith('https://www.youtube.com/')
  })

  it('only opens https URLs', async () => {
    const openExternal = vi.fn(async () => undefined)
    expect(validateOpenUrl('https://example.com/x').ok).toBe(true)
    expect(validateOpenUrl('http://example.com').ok).toBe(false)
    expect(validateOpenUrl('file:///etc/passwd').ok).toBe(false)
    expect(validateOpenUrl('javascript:alert(1)').ok).toBe(false)
    expect(validateOpenUrl('not a url').ok).toBe(false)
    await expect(openValidatedUrl('file:///etc/passwd', { openExternal })).rejects.toThrow()
    expect(openExternal).not.toHaveBeenCalled()
  })

  it('lists the allowlist for settings UI', () => {
    expect(listAllowedApps().length).toBeGreaterThan(0)
  })
})
