export interface ConfigFormat {
  version: number
  format: string
  schema: Record<string, unknown>
}

export interface ConfigMigration {
  fromVersion: number
  toVersion: number
  migrate: (config: Record<string, unknown>) => Record<string, unknown>
  description: string
}

const CONFIG_MIGRATIONS: ConfigMigration[] = [
  {
    fromVersion: 1,
    toVersion: 2,
    description: 'Migrate flat config to namespaced config',
    migrate: (config) => {
      const result: Record<string, unknown> = { ...config, _formatVersion: 2 }
      if (typeof config.theme === 'string') {
        result.general = { ...(result.general as Record<string, unknown> ?? {}), theme: config.theme }
        delete result.theme
      }
      if (typeof config.language === 'string') {
        result.general = { ...(result.general as Record<string, unknown> ?? {}), language: config.language }
        delete result.language
      }
      return result
    },
  },
]

const CURRENT_CONFIG_VERSION = 2

export function getConfigVersion(config: Record<string, unknown>): number {
  return (config._formatVersion as number) ?? 1
}

export function needsMigration(config: Record<string, unknown>): boolean {
  return getConfigVersion(config) < CURRENT_CONFIG_VERSION
}

export function migrateConfig(config: Record<string, unknown>): { config: Record<string, unknown>; applied: number } {
  let current = { ...config }
  let applied = 0

  for (const migration of CONFIG_MIGRATIONS) {
    if (getConfigVersion(current) === migration.fromVersion) {
      current = migration.migrate(current)
      current._formatVersion = migration.toVersion
      applied++
    }
  }

  return { config: current, applied }
}

export function getMigrationHistory(): ConfigMigration[] {
  return [...CONFIG_MIGRATIONS]
}

export function validateConfig(config: Record<string, unknown>): { valid: boolean; errors: string[] } {
  const errors: string[] = []
  const version = getConfigVersion(config)

  if (version < 1 || version > CURRENT_CONFIG_VERSION) {
    errors.push(`Unknown config format version: ${version}`)
  }

  return { valid: errors.length === 0, errors }
}

export function backupConfig(config: Record<string, unknown>): Record<string, unknown> {
  return {
    _backup: true,
    _backupAt: new Date().toISOString(),
    _originalVersion: getConfigVersion(config),
    ...config,
  }
}

export function rollbackConfig(backup: Record<string, unknown>): Record<string, unknown> {
  const result = { ...backup }
  delete result._backup
  delete result._backupAt
  delete result._originalVersion
  return result
}
