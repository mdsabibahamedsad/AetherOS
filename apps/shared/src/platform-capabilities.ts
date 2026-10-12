/**
 * AetherOS Platform Capability Registry — single source of truth.
 *
 * Values here MUST match actual implementations. Upgrade a cell only WITH
 * executable evidence (docs/AETHEROS_PLATFORM_RELEASE_MATRIX.md tracks the
 * evidence per cell):
 *
 * - Linux per-session values mirror electron/linux-session.cjs
 *   (`CAPABILITY_MATRIX`) exactly.
 * - iOS "backend-mediated" mirrors apps/ios MobileCapability (the device is a
 *   control plane; privileged execution happens server-side).
 * - Desktop reflects what apps/desktop actually ships today.
 *
 * Levels follow docs/AETHEROS_PLATFORM_ARCHITECTURE.md §6:
 *   native | backend-mediated | limited | unsupported
 */

export type CapabilityLevel = 'native' | 'backend-mediated' | 'limited' | 'unsupported'

export const CAPABILITY_KEYS = [
  'browser',
  'terminal',
  'filesystem',
  'computerUse',
  'notifications',
  'tray',
  'agentControl',
  'taskSubmission',
  'planPreview',
  'confirmations'
] as const

export type CapabilityKey = (typeof CAPABILITY_KEYS)[number]

export type PlatformId =
  | 'windows-desktop'
  | 'macos-desktop'
  | 'linux-desktop-x11'
  | 'linux-desktop-wayland'
  | 'ios'

export type PlatformCapabilities = Record<CapabilityKey, CapabilityLevel>

const native = (): PlatformCapabilities => ({
  browser: 'native',
  terminal: 'native',
  filesystem: 'native',
  computerUse: 'native',
  notifications: 'native',
  tray: 'native',
  agentControl: 'native',
  taskSubmission: 'native',
  planPreview: 'native',
  confirmations: 'native'
})

/** iOS is a control plane: privileged execution is always server-side. */
const iosCapabilities = (): PlatformCapabilities => ({
  browser: 'backend-mediated',
  terminal: 'backend-mediated',
  filesystem: 'unsupported',
  computerUse: 'backend-mediated',
  notifications: 'native',
  tray: 'unsupported',
  agentControl: 'native',
  taskSubmission: 'native',
  planPreview: 'native',
  confirmations: 'native'
})

/**
 * Linux Wayland: capture/input/window-management stay UNSUPPORTED until a
 * portal-based path is validated on real compositors (see linux-session.cjs).
 */
const waylandCapabilities = (): PlatformCapabilities => {
  const caps = native()
  caps.computerUse = 'unsupported'
  return caps
}

export const PLATFORM_CAPABILITIES: Record<PlatformId, PlatformCapabilities> = {
  'windows-desktop': native(),
  'macos-desktop': native(),
  'linux-desktop-x11': native(),
  'linux-desktop-wayland': waylandCapabilities(),
  ios: iosCapabilities()
}

/** Map a runtime platform + optional Linux session type to a registry entry. */
export function resolvePlatform(
  platform: 'win32' | 'darwin' | 'linux' | 'ios',
  linuxSession?: 'x11' | 'wayland' | 'x11-forwarded' | 'wslg' | 'headless'
): PlatformId | null {
  switch (platform) {
    case 'win32':
      return 'windows-desktop'
    case 'darwin':
      return 'macos-desktop'
    case 'ios':
      return 'ios'
    case 'linux':
      if (linuxSession === 'x11') return 'linux-desktop-x11'
      if (linuxSession === 'wayland') return 'linux-desktop-wayland'
      // Degraded/ambiguous sessions report the conservative X11 row's
      // desktop surface but callers must consult linux-session.cjs for the
      // per-capability truth on x11-forwarded/wslg/headless.
      return 'linux-desktop-x11'
    default:
      return null
  }
}

export function capabilityLevel(
  platform: PlatformId,
  key: CapabilityKey
): CapabilityLevel {
  return PLATFORM_CAPABILITIES[platform][key]
}

/** Shared confirmation language across platforms. */
export const APPROVAL_CHOICES = ['once', 'session', 'always', 'deny'] as const
export type ApprovalChoiceValue = (typeof APPROVAL_CHOICES)[number]

/** Shared task/run state semantics across platforms. */
export const RUN_STATES = [
  'queued',
  'running',
  'awaiting_approval',
  'completed',
  'failed',
  'stopped'
] as const
export type RunStateValue = (typeof RUN_STATES)[number]
