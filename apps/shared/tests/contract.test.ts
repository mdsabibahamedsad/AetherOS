import { resolvePlatform } from '@aetheros/shared'

describe('shared package public API contract', () => {
  it('resolvePlatform is a function', () => {
    expect(typeof resolvePlatform).toBe('function')
  })

  it('resolvePlatform returns correct platform for win32', () => {
    expect(resolvePlatform('win32')).toBe('windows-desktop')
  })

  it('resolvePlatform returns correct platform for darwin', () => {
    expect(resolvePlatform('darwin')).toBe('macos-desktop')
  })

  it('resolvePlatform returns correct platform for ios', () => {
    expect(resolvePlatform('ios')).toBe('ios')
  })

  it('resolvePlatform returns correct platform for linux with x11', () => {
    expect(resolvePlatform('linux', 'x11')).toBe('linux-desktop-x11')
  })

  it('resolvePlatform returns correct platform for linux with wayland', () => {
    expect(resolvePlatform('linux', 'wayland')).toBe('linux-desktop-wayland')
  })

  it('resolvePlatform returns null for unsupported platform', () => {
    expect(resolvePlatform('sunos')).toBeNull()
  })
})