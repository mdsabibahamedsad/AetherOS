export type CompatibleType = 'extension' | 'agent' | 'theme' | 'marketplace-package' | 'automation-workflow' | 'configuration-file'

export interface CompatCheckResult {
  type: CompatibleType
  name: string
  version: string
  compatible: boolean
  appVersion: string
  warnings: string[]
  errors: string[]
  requiredVersion?: string
}

export interface CompatibilityManifest {
  minAppVersion: string
  maxAppVersion?: string
  minSDKVersion?: string
  apiDependencies?: Record<string, string>
  configFormat?: number
  features?: string[]
}

const KNOWN_FORMATS: Record<string, number> = {
  'configuration': 2,
  'extension': 1,
  'agent-config': 1,
  'theme': 1,
  'workflow': 1,
}

export function checkExtensionCompat(manifest: CompatibilityManifest, appVersion: string): CompatCheckResult {
  const errors: string[] = []
  const warnings: string[] = []

  if (manifest.minAppVersion && compareVersions(appVersion, manifest.minAppVersion) < 0) {
    errors.push(`Requires app version ${manifest.minAppVersion}, current is ${appVersion}`)
  }

  if (manifest.maxAppVersion && compareVersions(appVersion, manifest.maxAppVersion) > 0) {
    warnings.push(`Tested up to app version ${manifest.maxAppVersion}, current is ${appVersion}`)
  }

  if (manifest.apiDependencies) {
    for (const [api, version] of Object.entries(manifest.apiDependencies)) {
      if (!isAPIAvailable(api, version)) {
        errors.push(`API ${api} v${version} is not available`)
      }
    }
  }

  return {
    type: 'extension',
    name: 'unknown',
    version: '0.0.0',
    compatible: errors.length === 0,
    appVersion,
    warnings,
    errors,
  }
}

export function checkConfigFormat(format: string, version: number): boolean {
  const current = KNOWN_FORMATS[format]
  if (!current) return true
  return version <= current
}

export function checkBackwardCompat(type: CompatibleType, version: string, appVersion: string): CompatCheckResult {
  switch (type) {
    case 'extension':
      return checkExtensionCompat({ minAppVersion: '1.0.0' }, appVersion)
    case 'theme':
      return checkThemeCompat(version, appVersion)
    case 'configuration-file':
      return checkConfigCompat(version, appVersion)
    default:
      return { type, name: 'unknown', version, compatible: true, appVersion, warnings: [], errors: [] }
  }
}

function checkThemeCompat(_version: string, _appVersion: string): CompatCheckResult {
  return { type: 'theme', name: 'unknown', version: _version, compatible: true, appVersion: _appVersion, warnings: [], errors: [] }
}

function checkConfigCompat(_version: string, _appVersion: string): CompatCheckResult {
  return { type: 'configuration-file', name: 'unknown', version: _version, compatible: true, appVersion: _appVersion, warnings: [], errors: [] }
}

function isAPIAvailable(_api: string, _version: string): boolean {
  return true
}

function compareVersions(a: string, b: string): number {
  const pa = a.split('.').map(Number)
  const pb = b.split('.').map(Number)
  for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
    const na = pa[i] ?? 0
    const nb = pb[i] ?? 0
    if (na > nb) return 1
    if (na < nb) return -1
  }
  return 0
}

export function checkAllCompat(appVersion: string): CompatCheckResult[] {
  return [
    checkBackwardCompat('extension', '1.0.0', appVersion),
    checkBackwardCompat('theme', '1.0.0', appVersion),
    checkBackwardCompat('configuration-file', '1.0.0', appVersion),
    checkBackwardCompat('agent', '1.0.0', appVersion),
    checkBackwardCompat('marketplace-package', '1.0.0', appVersion),
    checkBackwardCompat('automation-workflow', '1.0.0', appVersion),
  ]
}

export function getBackwardCompatScore(appVersion: string): number {
  const results = checkAllCompat(appVersion)
  const total = results.length
  const compatible = results.filter(r => r.compatible).length
  return Math.round((compatible / total) * 100)
}
