interface DeprecationRecord {
  api: string
  deprecatedIn: string
  removalIn: string
  replacement?: string
  migrationGuide?: string
  message: string
}

const deprecations: DeprecationRecord[] = []

export function registerDeprecation(record: DeprecationRecord) {
  deprecations.push(record)
}

export function checkApiDeprecation(apiName: string, appVersion: string): DeprecationRecord | null {
  const dep = deprecations.find(d => d.api === apiName)
  if (!dep) return null
  return dep
}

export function getActiveDeprecations(appVersion: string): DeprecationRecord[] {
  return deprecations.filter(d => {
    const removal = d.removalIn.split('.').map(Number)
    const current = appVersion.split('.').map(Number)
    for (let i = 0; i < 3; i++) {
      if ((current[i] ?? 0) < (removal[i] ?? 0)) return true
      if ((current[i] ?? 0) > (removal[i] ?? 0)) return false
    }
    return true
  })
}

export function getRemovedApis(appVersion: string): DeprecationRecord[] {
  return deprecations.filter(d => {
    const removal = d.removalIn.split('.').map(Number)
    const current = appVersion.split('.').map(Number)
    for (let i = 0; i < 3; i++) {
      if ((current[i] ?? 0) < (removal[i] ?? 0)) return false
      if ((current[i] ?? 0) > (removal[i] ?? 0)) return true
    }
    return true
  })
}

export function shouldWarn(apiName: string, appVersion: string): boolean {
  const dep = checkApiDeprecation(apiName, appVersion)
  if (!dep) return false

  const removal = dep.removalIn.split('.').map(Number)
  const current = appVersion.split('.').map(Number)

  for (let i = 0; i < 3; i++) {
    if ((current[i] ?? 0) < (removal[i] ?? 0) - 1) return false
    if ((current[i] ?? 0) > (removal[i] ?? 0)) return true
  }
  return true
}

export function getMigrationPath(apiName: string): string | null {
  const dep = deprecations.find(d => d.api === apiName)
  return dep?.migrationGuide ?? null
}

export function checkPluginCompatibility(pluginVersion: string, apiVersion: string): {
  compatible: boolean
  warnings: string[]
  errors: string[]
} {
  const warnings: string[] = []
  const errors: string[] = []

  for (const dep of deprecations) {
    if (dep.removalIn && compareVersions(pluginVersion, dep.removalIn) >= 0) {
      errors.push(`API "${dep.api}" was removed in ${dep.removalIn}. Plugin targets ${pluginVersion}.`)
    }
    if (dep.deprecatedIn && shouldWarn(dep.api, pluginVersion)) {
      warnings.push(`API "${dep.api}" is deprecated in ${dep.deprecatedIn}. ${dep.replacement ? `Use "${dep.replacement}" instead.` : ''}`)
    }
  }

  return {
    compatible: errors.length === 0,
    warnings,
    errors,
  }
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
