/**
 * CI-safe diagnostic test for @aetheros/shared package resolution.
 * 
 * This test verifies that @aetheros/shared resolves correctly from the
 * installed workspace package without depending on developer-specific paths,
 * Windows paths, npm links, or IDE configuration.
 * 
 * It must work on Windows, Linux, and macOS.
 */
import { resolvePlatform } from '@aetheros/shared'

describe('shared package CI resolution contract', () => {
  it('resolvePlatform is a function', () => {
    // Verify the function exists and is callable
    expect(typeof resolvePlatform).toBe('function')
  })

  it('resolvePlatform maps win32 to windows-desktop', () => {
    const result = resolvePlatform('win32')
    expect(result).toBe('windows-desktop')
  })

  it('resolvePlatform maps darwin to macos-desktop', () => {
    const result = resolvePlatform('darwin')
    expect(result).toBe('macos-desktop')
  })

  it('resolvePlatform maps ios to ios', () => {
    const result = resolvePlatform('ios')
    expect(result).toBe('ios')
  })

  it('resolvePlatform maps linux with x11 to linux-desktop-x11', () => {
    const result = resolvePlatform('linux', 'x11')
    expect(result).toBe('linux-desktop-x11')
  })

  it('resolvePlatform maps linux with wayland to linux-desktop-wayland', () => {
    const result = resolvePlatform('linux', 'wayland')
    expect(result).toBe('linux-desktop-wayland')
  })

  it('resolvePlatform returns null for unsupported platform', () => {
    // 'sunos' is not a supported platform in the resolvePlatform function
    const result = resolvePlatform('sunos')
    expect(result).toBeNull()
  })
})