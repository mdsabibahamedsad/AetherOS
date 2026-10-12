export type LTSChannel = 'nightly' | 'beta' | 'stable' | 'lts' | 'security-patch' | 'emergency-hotfix'
export type LTSPhase = 'active' | 'maintenance' | 'security' | 'eol'

export interface LTSConfig {
  channel: LTSChannel
  autoUpdate: boolean
  allowDowngrade: boolean
  notifyForUpdates: boolean
  updateCheckInterval: number
  proxy?: string
  allowedChannels: LTSChannel[]
  pinnedVersion?: string
  backportOnly: boolean
}

export interface LTSRelease {
  version: string
  channel: LTSChannel
  releasedAt: string
  eolAt: string
  phase: LTSPhase
  changelog: string
  migrationGuide?: string
  knownIssues: string[]
  securityPatches: string[]
}

export interface LTSLifecycle {
  activeUntil: string
  maintenanceUntil: string
  securityUntil: string
  eolAt: string
}

export const LTS_RELEASES: LTSRelease[] = [
  {
    version: '1.0.0',
    channel: 'lts',
    releasedAt: '2026-07-23',
    eolAt: '2028-07-23',
    phase: 'active',
    changelog: 'Initial LTS release — production-hardened desktop platform',
    knownIssues: [],
    securityPatches: [],
  },
]

export const LTS_LIFECYCLE: LTSLifecycle = {
  activeUntil: '2027-01-23',
  maintenanceUntil: '2028-01-23',
  securityUntil: '2028-07-23',
  eolAt: '2028-07-23',
}

export function getLTSChannelPriority(channel: LTSChannel): number {
  const order: Record<LTSChannel, number> = {
    'emergency-hotfix': 6,
    'security-patch': 5,
    lts: 4,
    stable: 3,
    beta: 2,
    nightly: 1,
  }
  return order[channel] ?? 0
}

export function isChannelActive(channel: LTSChannel): boolean {
  return channel !== 'emergency-hotfix'
}

export function getLTSEolDate(version: string): string | null {
  const release = LTS_RELEASES.find(r => r.version === version)
  return release?.eolAt ?? null
}

export function isVersionExpired(version: string): boolean {
  const eol = getLTSEolDate(version)
  if (!eol) return false
  return new Date(eol) < new Date()
}
