export type ReleaseType = 'patch' | 'minor' | 'major' | 'lts' | 'hotfix'

export interface ReleasePlan {
  type: ReleaseType
  currentVersion: string
  nextVersion: string
  channel: string
  isCritical: boolean
  changes: string[]
  affectedModules: string[]
  requiresMigration: boolean
  estimatedEffort: 'small' | 'medium' | 'large'
}

export interface ReleaseArtifact {
  platform: string
  arch: string
  format: string
  path: string
  checksum: string
  signature?: string
  size: number
}

export interface ReleaseManifest {
  version: string
  channel: string
  type: ReleaseType
  releasedAt: string
  artifacts: ReleaseArtifact[]
  changelog: string[]
  migrationGuide?: string
  securityPatches: string[]
  knownIssues: string[]
  signedBy: string
}

class ReleaseManager {
  generateReleasePlan(type: ReleaseType, currentVersion: string, changes: string[]): ReleasePlan {
    const nextVersion = this.bumpVersion(currentVersion, type)
    const channel = type === 'lts' ? 'lts' : type === 'hotfix' ? 'emergency-hotfix' : 'stable'

    return {
      type,
      currentVersion,
      nextVersion,
      channel,
      isCritical: type === 'hotfix',
      changes,
      affectedModules: this.getAffectedModules(changes),
      requiresMigration: type === 'major' || type === 'lts',
      estimatedEffort: type === 'hotfix' ? 'small' : type === 'patch' ? 'small' : type === 'minor' ? 'medium' : 'large',
    }
  }

  bumpVersion(version: string, type: ReleaseType): string {
    const parts = version.split('.').map(Number)
    const [major, minor, patch] = parts

    switch (type) {
      case 'major': return `${major + 1}.0.0`
      case 'minor': return `${major}.${minor + 1}.0`
      case 'patch': return `${major}.${minor}.${patch + 1}`
      case 'hotfix': return `${major}.${minor}.${patch + 1}-hotfix.1`
      case 'lts': return `${major}.${minor}.${patch}-lts.1`
      default: return version
    }
  }

  generateChangelog(version: string, changes: string[], type: ReleaseType): string[] {
    const date = new Date().toISOString().split('T')[0]
    const header = `## v${version} (${date})`

    const sections: string[] = [header, '']
    const categories: Record<string, string[]> = {
      'Added': [],
      'Changed': [],
      'Deprecated': [],
      'Removed': [],
      'Fixed': [],
      'Security': [],
    }

    for (const change of changes) {
      let categorized = false
      for (const [category] of Object.entries(categories)) {
        if (change.startsWith(`[${category.toLowerCase()}]`) || change.startsWith(`${category}:`)) {
          categories[category].push(change.replace(/^\[.*?\]\s*/, '').replace(/^\w+:\s*/, ''))
          categorized = true
          break
        }
      }
      if (!categorized) {
        categories['Changed'].push(change)
      }
    }

    for (const [category, items] of Object.entries(categories)) {
      if (items.length > 0) {
        sections.push(`### ${category}`)
        for (const item of items) {
          sections.push(`- ${item}`)
        }
        sections.push('')
      }
    }

    if (type === 'hotfix') {
      sections.push('### Hotfix')
      sections.push('- This release contains urgent fixes for a critical issue.')
      sections.push('- All users on affected versions are strongly recommended to update.')
      sections.push('')
    }

    if (type === 'lts') {
      sections.push('### Long-Term Support')
      sections.push(`- This release is designated as an LTS release with 24 months of support.`)
      sections.push(`- Critical and security fixes only after the active development phase.`)
      sections.push('')
    }

    return sections
  }

  generateMigrationGuide(fromVersion: string, toVersion: string, changes: string[]): string {
    const breakingChanges = changes.filter(c =>
      c.toLowerCase().includes('breaking') || c.toLowerCase().includes('deprecat') || c.toLowerCase().includes('remove')
    )
    return [
      `# Migration Guide: ${fromVersion} → ${toVersion}`,
      '',
      `## Overview`,
      `This guide covers migration from v${fromVersion} to v${toVersion}.`,
      '',
      breakingChanges.length > 0 ? '## Breaking Changes\n' + breakingChanges.map(c => `- ${c}`).join('\n') : '*No breaking changes*',
      '',
      '## Rollback',
      'To roll back, reinstall the previous version from the releases page.',
      '',
    ].join('\n')
  }

  validateRelease(plan: ReleasePlan): { valid: boolean; errors: string[]; warnings: string[] } {
    const errors: string[] = []
    const warnings: string[] = []

    if (plan.changes.length === 0) {
      warnings.push('Release has no changes listed')
    }

    if (plan.requiresMigration && !plan.changes.some(c => c.toLowerCase().includes('migration'))) {
      warnings.push('Major/LTS release should include migration instructions')
    }

    return { valid: errors.length === 0, errors, warnings }
  }

  private getAffectedModules(changes: string[]): string[] {
    const modules = new Set<string>()
    const moduleMap: Record<string, RegExp> = {
      'Core': /core|kernel|runtime/i,
      'UI': /ui|component|view|renderer/i,
      'API': /api|sdk|endpoint|ipc/i,
      'Plugin System': /plugin|extension/i,
      'Security': /security|auth|crypto|permission/i,
      'Performance': /performance|memory|speed|optimize/i,
      'Documentation': /doc|readme|guide|manual/i,
      'Build': /build|ci|cd|pipeline/i,
      'Storage': /storage|database|migration|file/i,
      'Network': /network|sync|gateway|connection/i,
    }

    for (const change of changes) {
      for (const [module, pattern] of Object.entries(moduleMap)) {
        if (pattern.test(change)) {
          modules.add(module)
        }
      }
    }

    return Array.from(modules)
  }
}

export const releaseManager = new ReleaseManager()
