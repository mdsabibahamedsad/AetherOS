import {
  APPROVAL_CHOICES,
  CAPABILITY_KEYS,
  type CapabilityKey,
  capabilityLevel,
  PLATFORM_CAPABILITIES,
  resolvePlatform,
  RUN_STATES
} from '@aetheros/shared'
import { describe, expect, it } from 'vitest'

// Behavior contracts for the capability registry — invariants, not snapshots.
// Cell values may be upgraded with executable evidence; these assertions must
// keep holding when that happens.

const ALL_KEYS = CAPABILITY_KEYS as readonly CapabilityKey[]

describe('platform capability registry', () => {
  it('every platform defines every capability with a known level', () => {
    const levels = new Set(['native', 'backend-mediated', 'limited', 'unsupported'])

    for (const [platform, caps] of Object.entries(PLATFORM_CAPABILITIES)) {
      for (const key of ALL_KEYS) {
        expect(levels.has(caps[key]), `${platform}.${key} has a defined level`).toBe(true)
      }
    }
  })

  it('desktop platforms always keep agent control-plane capabilities native', () => {
    for (const platform of ['windows-desktop', 'macos-desktop', 'linux-desktop-x11', 'linux-desktop-wayland'] as const) {
      for (const key of ['agentControl', 'taskSubmission', 'confirmations'] as const) {
        expect(capabilityLevel(platform, key), `${platform}.${key}`).toBe('native')
      }
    }
  })

  it('iOS never claims privileged desktop execution natively', () => {
    for (const key of ['browser', 'terminal', 'computerUse'] as const) {
      expect(capabilityLevel('ios', key)).not.toBe('native')
    }

    expect(capabilityLevel('ios', 'filesystem')).toBe('unsupported')
    // ...but the control plane itself IS native on iOS.
    expect(capabilityLevel('ios', 'agentControl')).toBe('native')
    expect(capabilityLevel('ios', 'notifications')).toBe('native')
  })

  it('Wayland degrades only what the Linux module marks unsupported', () => {
    // Mirrors electron/linux-session.cjs: capture/input/window-management are
    // unsupported under Wayland; everything else stays at least limited.
    expect(capabilityLevel('linux-desktop-wayland', 'computerUse')).toBe('unsupported')
    expect(capabilityLevel('linux-desktop-x11', 'computerUse')).toBe('native')
  })

  it('resolvePlatform maps runtimes to registry entries and never throws', () => {
    expect(resolvePlatform('win32')).toBe('windows-desktop')
    expect(resolvePlatform('darwin')).toBe('macos-desktop')
    expect(resolvePlatform('ios')).toBe('ios')
    expect(resolvePlatform('linux', 'wayland')).toBe('linux-desktop-wayland')
    expect(resolvePlatform('linux', 'x11')).toBe('linux-desktop-x11')
    expect(resolvePlatform('sunos' as never)).toBeNull()
  })
})

describe('module contract (CI #8 regression)', () => {
  it('exposes resolvePlatform/capabilityLevel as callable functions', () => {
    // Guards the stale-dist failure mode where the @aetheros/shared import
    // resolved to an empty module object ("resolvePlatform is not a function").
    expect(typeof resolvePlatform).toBe('function')
    expect(typeof capabilityLevel).toBe('function')
  })

  it('registry entries are deterministic across repeated lookups', () => {
    for (const platform of Object.keys(PLATFORM_CAPABILITIES)) {
      for (const key of ALL_KEYS) {
        const pid = platform as Parameters<typeof capabilityLevel>[0]
        expect(capabilityLevel(pid, key)).toBe(capabilityLevel(pid, key))
        expect(capabilityLevel(pid, key)).toBe(PLATFORM_CAPABILITIES[pid][key])
      }
    }

    expect(resolvePlatform('win32')).toBe(resolvePlatform('win32'))
    expect(resolvePlatform('linux', 'wayland')).toBe(resolvePlatform('linux', 'wayland'))
  })

  it('registry covers exactly the known platform ids, nothing more', () => {
    expect(Object.keys(PLATFORM_CAPABILITIES).sort()).toEqual(
      ['ios', 'linux-desktop-wayland', 'linux-desktop-x11', 'macos-desktop', 'windows-desktop'].sort(),
    )
  })
})

describe('shared semantics', () => {
  it('approval choices match the backend contract exactly', () => {
    expect(APPROVAL_CHOICES).toEqual(['once', 'session', 'always', 'deny'])
  })

  it('run states cover every state the wire can report', () => {
    for (const s of ['queued', 'running', 'awaiting_approval', 'completed', 'failed', 'stopped']) {
      expect(RUN_STATES).toContain(s)
    }

    expect(new Set(RUN_STATES).size).toBe(RUN_STATES.length)
  })
})
