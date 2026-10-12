export type SDKVersion = 'v1' | 'v2'
export type SDKCompatLevel = 'full' | 'partial' | 'deprecated' | 'removed'

export interface SDKManifest {
  sdkVersion: SDKVersion
  apiVersion: string
  minAppVersion: string
  maxAppVersion: string
  releasedAt: string
  deprecatedAt?: string
  removedAt?: string
  compatLevel: SDKCompatLevel
  breakingChanges: string[]
  migrationGuide?: string
}

export const SDK_MANIFESTS: SDKManifest[] = [
  {
    sdkVersion: 'v1',
    apiVersion: '1.0.0',
    minAppVersion: '1.0.0',
    maxAppVersion: '1.9999.9999',
    releasedAt: '2026-07-23',
    compatLevel: 'full',
    breakingChanges: [],
  },
]

export interface SDKFeature {
  name: string
  introducedIn: SDKVersion
  deprecatedIn?: SDKVersion
  removedIn?: SDKVersion
  replacement?: string
}

export const SDK_FEATURES: SDKFeature[] = [
  { name: 'plugin.registerTool', introducedIn: 'v1' },
  { name: 'plugin.onSessionStart', introducedIn: 'v1' },
  { name: 'plugin.onSessionEnd', introducedIn: 'v1' },
  { name: 'plugin.onToolCall', introducedIn: 'v1' },
  { name: 'plugin.onToolResult', introducedIn: 'v1' },
  { name: 'plugin.registerHook', introducedIn: 'v1' },
  { name: 'plugin.getConfig', introducedIn: 'v1' },
  { name: 'plugin.setConfig', introducedIn: 'v1' },
  { name: 'plugin.getLogger', introducedIn: 'v1' },
  { name: 'plugin.registerCLICommand', introducedIn: 'v1' },
  { name: 'plugin.registerTheme', introducedIn: 'v1' },
  { name: 'plugin.registerProvider', introducedIn: 'v1' },
  { name: 'api.getSystemInfo', introducedIn: 'v1' },
  { name: 'api.getPerformanceMetrics', introducedIn: 'v1' },
  { name: 'api.readFile', introducedIn: 'v1' },
  { name: 'api.writeFile', introducedIn: 'v1' },
  { name: 'api.dialog.open', introducedIn: 'v1' },
  { name: 'api.notification.show', introducedIn: 'v1' },
  { name: 'api.updater.check', introducedIn: 'v1' },
  { name: 'api.updater.install', introducedIn: 'v1' },
  { name: 'api.telemetry.event', introducedIn: 'v1' },
  { name: 'api.telemetry.metric', introducedIn: 'v1' },
  { name: 'api.error.report', introducedIn: 'v1' },
  { name: 'api.migration.run', introducedIn: 'v1' },
  { name: 'api.migration.status', introducedIn: 'v1' },
]

export function getCurrentSDKVersion(): SDKVersion {
  return 'v1'
}

export function isFeatureSupported(feature: string, sdkVersion: SDKVersion): boolean {
  const feat = SDK_FEATURES.find(f => f.name === feature)
  if (!feat) return false
  if (feat.removedIn && sdkVersion >= feat.removedIn) return false
  if (feat.introducedIn > sdkVersion) return false
  return true
}

export function getDeprecatedFeatures(sdkVersion: SDKVersion): SDKFeature[] {
  return SDK_FEATURES.filter(f => f.deprecatedIn && f.deprecatedIn <= sdkVersion && (!f.removedIn || f.removedIn > sdkVersion))
}

export function getRemovedFeatures(sdkVersion: SDKVersion): SDKFeature[] {
  return SDK_FEATURES.filter(f => f.removedIn && f.removedIn <= sdkVersion)
}

export function getCompatibilityLevel(appVersion: string, sdkVersion: SDKVersion): SDKCompatLevel {
  const manifest = SDK_MANIFESTS.find(m => m.sdkVersion === sdkVersion)
  if (!manifest) return 'removed'
  if (manifest.removedAt && new Date() > new Date(manifest.removedAt)) return 'removed'
  if (manifest.deprecatedAt && new Date() > new Date(manifest.deprecatedAt)) return 'deprecated'
  if (appVersion < manifest.minAppVersion) return 'partial'
  if (appVersion > manifest.maxAppVersion) return 'partial'
  return 'full'
}
