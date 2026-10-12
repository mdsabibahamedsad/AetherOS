export type DependencyIssueType = 'deprecated' | 'vulnerability' | 'license' | 'unused' | 'duplicate'

export interface DependencyIssue {
  type: DependencyIssueType
  package: string
  version: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  description: string
  recommendation?: string
  fixedIn?: string
  cveId?: string
}

export interface DependencyInfo {
  name: string
  version: string
  latestVersion?: string
  license?: string
  deprecated: boolean
  hasVulnerabilities: boolean
  vulnerabilities: DependencyIssue[]
  isUnused: boolean
  isDuplicate: boolean
  usageCount?: number
  bundleSize?: number
}

export interface DependencyAuditResult {
  total: number
  deprecated: number
  vulnerable: number
  licenseIssues: number
  unused: number
  duplicates: number
  issues: DependencyIssue[]
  score: number
  recommendations: string[]
}

class DependencyManager {
  private registry: Map<string, DependencyInfo> = new Map()
  private knownVulnerabilities: Map<string, DependencyIssue[]> = new Map()

  registerPackage(info: DependencyInfo) {
    this.registry.set(info.name, info)
  }

  getPackage(name: string): DependencyInfo | undefined {
    return this.registry.get(name)
  }

  getRegistry(): Map<string, DependencyInfo> {
    return new Map(this.registry)
  }

  getAllPackages(): DependencyInfo[] {
    return Array.from(this.registry.values())
  }

  getDeprecated(): DependencyInfo[] {
    return this.getAllPackages().filter(p => p.deprecated)
  }

  getVulnerable(): DependencyInfo[] {
    return this.getAllPackages().filter(p => p.hasVulnerabilities)
  }

  getUnused(): DependencyInfo[] {
    return this.getAllPackages().filter(p => p.isUnused)
  }

  getDuplicates(): DependencyInfo[] {
    return this.getAllPackages().filter(p => p.isDuplicate)
  }

  audit(): DependencyAuditResult {
    const all = this.getAllPackages()
    const issues: DependencyIssue[] = []

    for (const pkg of all) {
      issues.push(...pkg.vulnerabilities)
      if (pkg.deprecated) {
        issues.push({
          type: 'deprecated', package: pkg.name, version: pkg.version,
          severity: 'medium', description: `Package "${pkg.name}" is deprecated`,
          recommendation: pkg.latestVersion ? `Update to ${pkg.latestVersion}` : 'Find alternative',
        })
      }
      if (pkg.isUnused) {
        issues.push({
          type: 'unused', package: pkg.name, version: pkg.version,
          severity: 'low', description: `Package "${pkg.name}" appears unused`,
          recommendation: 'Consider removing this dependency',
        })
      }
      if (pkg.isDuplicate) {
        issues.push({
          type: 'duplicate', package: pkg.name, version: pkg.version,
          severity: 'low', description: `Package "${pkg.name}" appears multiple times`,
          recommendation: 'Deduplicate package versions',
        })
      }
    }

    const deprecated = this.getDeprecated().length
    const vulnerable = this.getVulnerable().length
    const licenseIssues = all.filter(p => !p.license).length
    const unused = this.getUnused().length
    const duplicates = this.getDuplicates().length

    const score = Math.max(0, 100 - (vulnerable * 10) - (deprecated * 5) - (licenseIssues * 3) - (unused * 2) - (duplicates * 2))

    const recommendations: string[] = []
    if (vulnerable > 0) recommendations.push(`Fix ${vulnerable} vulnerable package(s) immediately`)
    if (deprecated > 0) recommendations.push(`Replace ${deprecated} deprecated package(s)`)
    if (unused > 0) recommendations.push(`Remove ${unused} unused package(s)`)
    if (duplicates > 0) recommendations.push(`Deduplicate ${duplicates} package version(s)`)

    return { total: all.length, deprecated, vulnerable, licenseIssues, unused, duplicates, issues, score, recommendations }
  }

  registerVulnerability(packageName: string, issue: DependencyIssue) {
    const existing = this.knownVulnerabilities.get(packageName) || []
    existing.push(issue)
    this.knownVulnerabilities.set(packageName, existing)

    const pkg = this.registry.get(packageName)
    if (pkg) {
      pkg.hasVulnerabilities = true
      pkg.vulnerabilities.push(issue)
    }
  }

  checkForUpdates(): Array<{ name: string; current: string; latest: string; type: 'major' | 'minor' | 'patch' }> {
    const updates: Array<{ name: string; current: string; latest: string; type: 'major' | 'minor' | 'patch' }> = []
    for (const pkg of this.getAllPackages()) {
      if (pkg.latestVersion && pkg.version !== pkg.latestVersion) {
        const currentParts = pkg.version.split('.').map(Number)
        const latestParts = pkg.latestVersion.split('.').map(Number)
        let type: 'major' | 'minor' | 'patch' = 'patch'
        if (latestParts[0] > currentParts[0]) type = 'major'
        else if (latestParts[1] > currentParts[1]) type = 'minor'
        updates.push({ name: pkg.name, current: pkg.version, latest: pkg.latestVersion, type })
      }
    }
    return updates
  }

  getHealthScore(): number {
    return this.audit().score
  }
}

export const dependencyManager = new DependencyManager()
