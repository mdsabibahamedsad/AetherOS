export type MigrationType = 'config' | 'workspace' | 'knowledge' | 'models' | 'extensions' | 'cloud-sync' | 'database'

export interface Migration {
  id: string
  name: string
  type: MigrationType
  version: string
  description: string
  dependsOn?: string[]
  checksum?: string
  apply: () => Promise<MigrationResult>
  rollback: () => Promise<MigrationResult>
  validate: () => Promise<ValidationResult>
  backup: () => Promise<void>
  estimateDuration?: number
}

export interface MigrationResult {
  success: boolean
  applied: number
  rolledBack: number
  errors: string[]
  warnings: string[]
  duration: number
  details?: Record<string, unknown>
}

export interface ValidationResult {
  valid: boolean
  errors: string[]
  warnings: string[]
  details?: Record<string, unknown>
}

interface MigrationState {
  applied: string[]
  failed: string[]
  inProgress: string | null
  lastRun?: string
  lastSuccess?: string
  lastError?: string
}

const MIGRATION_STATE_KEY = 'aetheros.migration.state'
const MIGRATION_BACKUP_KEY = 'aetheros.migration.backup'

class MigrationEngine {
  private migrations: Map<string, Migration> = new Map()
  private state: MigrationState = { applied: [], failed: [], inProgress: null }

  constructor() {
    this.loadState()
  }

  register(migration: Migration) {
    this.migrations.set(migration.id, migration)
  }

  registerMany(migrations: Migration[]) {
    for (const m of migrations) {
      this.register(m)
    }
  }

  getMigration(id: string): Migration | undefined {
    return this.migrations.get(id)
  }

  listMigrations(type?: MigrationType): Migration[] {
    const all = Array.from(this.migrations.values())
    return type ? all.filter(m => m.type === type) : all
  }

  getPendingMigrations(): Migration[] {
    return this.listMigrations().filter(m => !this.state.applied.includes(m.id) && !this.state.failed.includes(m.id))
  }

  async applyMigration(id: string): Promise<MigrationResult> {
    const migration = this.migrations.get(id)
    if (!migration) {
      return { success: false, applied: 0, rolledBack: 0, errors: [`Migration "${id}" not found`], warnings: [], duration: 0 }
    }

    if (this.state.applied.includes(id)) {
      return { success: true, applied: 0, rolledBack: 0, errors: [], warnings: ['Already applied'], duration: 0 }
    }

    const startTime = Date.now()

    try {
      this.state.inProgress = id
      this.saveState()

      await migration.backup()
      const validation = await migration.validate()
      if (!validation.valid) {
        this.state.failed.push(id)
        this.state.inProgress = null
        this.saveState()
        return { success: false, applied: 0, rolledBack: 0, errors: validation.errors, warnings: validation.warnings, duration: Date.now() - startTime }
      }

      const result = await migration.apply()

      if (result.success) {
        this.state.applied.push(id)
        this.state.lastSuccess = new Date().toISOString()
      } else {
        this.state.failed.push(id)
        this.state.lastError = result.errors.join('; ')
      }

      this.state.inProgress = null
      this.state.lastRun = new Date().toISOString()
      this.saveState()

      return { ...result, duration: Date.now() - startTime }
    } catch (error) {
      this.state.failed.push(id)
      this.state.inProgress = null
      this.state.lastError = String(error)
      this.saveState()
      return { success: false, applied: 0, rolledBack: 0, errors: [String(error)], warnings: [], duration: Date.now() - startTime }
    }
  }

  async rollbackMigration(id: string): Promise<MigrationResult> {
    const migration = this.migrations.get(id)
    if (!migration) {
      return { success: false, applied: 0, rolledBack: 0, errors: [`Migration "${id}" not found`], warnings: [], duration: 0 }
    }

    const startTime = Date.now()

    try {
      const result = await migration.rollback()

      if (result.success) {
        this.state.applied = this.state.applied.filter(a => a !== id)
        this.state.failed = this.state.failed.filter(f => f !== id)
        this.saveState()
      }

      return { ...result, duration: Date.now() - startTime }
    } catch (error) {
      return { success: false, applied: 0, rolledBack: 0, errors: [String(error)], warnings: [], duration: Date.now() - startTime }
    }
  }

  async applyAllPending(): Promise<MigrationResult> {
    const pending = this.getPendingMigrations()
    const sorted = this.topologicalSort(pending)
    const errors: string[] = []
    const warnings: string[] = []
    let applied = 0
    let rolledBack = 0
    const startTime = Date.now()

    for (const migration of sorted) {
      const result = await this.applyMigration(migration.id)
      if (result.success) {
        applied++
      } else {
        errors.push(...result.errors)
        warnings.push(...result.warnings)
        await this.rollbackMigration(migration.id)
        rolledBack++
      }
    }

    return { success: errors.length === 0, applied, rolledBack, errors, warnings, duration: Date.now() - startTime }
  }

  getState(): MigrationState {
    return { ...this.state }
  }

  isMigrationApplied(id: string): boolean {
    return this.state.applied.includes(id)
  }

  private topologicalSort(migrations: Migration[]): Migration[] {
    const visited = new Set<string>()
    const sorted: Migration[] = []
    const map = new Map(migrations.map(m => [m.id, m]))

    function visit(id: string) {
      if (visited.has(id)) return
      visited.add(id)
      const m = map.get(id)
      if (m?.dependsOn) {
        for (const dep of m.dependsOn) {
          visit(dep)
        }
      }
      const migration = map.get(id)
      if (migration) sorted.push(migration)
    }

    for (const m of migrations) {
      visit(m.id)
    }

    return sorted
  }

  private loadState() {
    try {
      const raw = window.localStorage.getItem(MIGRATION_STATE_KEY)
      if (raw) {
        this.state = JSON.parse(raw)
      }
    } catch {
      this.state = { applied: [], failed: [], inProgress: null }
    }
  }

  private saveState() {
    try {
      window.localStorage.setItem(MIGRATION_STATE_KEY, JSON.stringify(this.state))
    } catch {
      console.error('Failed to save migration state')
    }
  }
}

export const migrationEngine = new MigrationEngine()
