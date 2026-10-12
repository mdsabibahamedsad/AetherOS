export type PluginSDKAPI = Record<string, (...args: unknown[]) => unknown>

export interface CompatMapping {
  from: string
  to: string
  transform: (...args: unknown[]) => unknown[]
  since: string
  until?: string
}

export interface DeprecationWarning {
  api: string
  message: string
  migrationGuide: string
  deprecatedIn: string
  removalIn: string
}

export const COMPAT_MAPPINGS: CompatMapping[] = []

export function registerCompatMapping(mapping: CompatMapping) {
  COMPAT_MAPPINGS.push(mapping)
}

export function wrapWithCompatibility(sdk: PluginSDKAPI, version: string): PluginSDKAPI {
  const wrapped: PluginSDKAPI = { ...sdk }

  for (const mapping of COMPAT_MAPPINGS) {
    const originalFn = wrapped[mapping.to]
    if (originalFn) {
      wrapped[mapping.from] = (...args: unknown[]) => {
        const transformed = mapping.transform(...args)
        return originalFn(...transformed)
      }
    }
  }

  return wrapped
}

export const SDK_DEPRECATIONS: DeprecationWarning[] = []

export function registerDeprecation(deprecation: DeprecationWarning) {
  SDK_DEPRECATIONS.push(deprecation)
}

export function getDeprecationWarnings(apiName: string): DeprecationWarning[] {
  return SDK_DEPRECATIONS.filter(d => d.api === apiName)
}

export function checkDeprecatedCalls(sdk: Record<string, unknown>): DeprecationWarning[] {
  const warnings: DeprecationWarning[] = []
  for (const key of Object.keys(sdk)) {
    const deprecations = getDeprecationWarnings(key)
    warnings.push(...deprecations)
  }
  return warnings
}

export interface SDKCompatReport {
  sdkVersion: string
  appVersion: string
  level: 'full' | 'partial' | 'deprecated' | 'removed'
  activeDeprecations: DeprecationWarning[]
  compatMappings: CompatMapping[]
  supportedFeatures: number
  totalFeatures: number
}

export function generateCompatReport(sdkVersion: string, appVersion: string): SDKCompatReport {
  const level = getSDKCompatLevel(sdkVersion, appVersion)
  return {
    sdkVersion,
    appVersion,
    level,
    activeDeprecations: SDK_DEPRECATIONS.filter(d => {
      const removedIn = parseVersion(d.removalIn)
      const current = parseVersion(appVersion)
      return current < removedIn
    }),
    compatMappings: COMPAT_MAPPINGS.filter(m => !m.until || parseVersion(appVersion) <= parseVersion(m.until)),
    supportedFeatures: 25,
    totalFeatures: 25,
  }
}

export function parseVersion(v: string): number[] {
  return v.split('.').map(Number)
}

export function compareVersions(a: string, b: string): number {
  const pa = parseVersion(a)
  const pb = parseVersion(b)
  for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
    const na = pa[i] ?? 0
    const nb = pb[i] ?? 0
    if (na > nb) return 1
    if (na < nb) return -1
  }
  return 0
}

export function getSDKCompatLevel(sdkVersion: string, appVersion: string): 'full' | 'partial' | 'deprecated' | 'removed' {
  if (compareVersions(appVersion, '1.0.0') < 0) return 'partial'
  if (compareVersions(appVersion, '2.0.0') >= 0) return 'partial'
  if (compareVersions(appVersion, '1.5.0') >= 0) return 'deprecated'
  return 'full'
}

export class SDKCompatLayer {
  private apiVersions: Map<string, string> = new Map()

  registerAPIVersion(name: string, version: string) {
    this.apiVersions.set(name, version)
  }

  getAPIVersion(name: string): string | undefined {
    return this.apiVersions.get(name)
  }

  checkCompat(name: string, requestedVersion: string): boolean {
    const actualVersion = this.apiVersions.get(name)
    if (!actualVersion) return false
    return compareVersions(requestedVersion, actualVersion) <= 0
  }
}
