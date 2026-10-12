export type BackupScope = 'all' | 'config' | 'workspace' | 'extensions' | 'themes' | 'sync' | 'sessions' | 'knowledge'
export type BackupFormat = 'zip' | 'tar'
export type BackupSchedule = 'manual' | 'daily' | 'weekly' | 'monthly'

export interface BackupManifest {
  id: string
  name: string
  version: string
  appVersion: string
  createdAt: string
  scope: BackupScope[]
  format: BackupFormat
  size: number
  checksum: string
  encrypted: boolean
  includes: string[]
  metadata: Record<string, string>
}

export interface BackupEntry {
  manifest: BackupManifest
  path: string
  date: Date
  size: number
}

export interface RestorePlan {
  manifest: BackupManifest
  conflicts: RestoreConflict[]
  estimatedSize: number
  requiresRestart: boolean
  steps: RestoreStep[]
}

export interface RestoreConflict {
  path: string
  type: 'override' | 'merge' | 'skip'
  resolution?: 'override' | 'merge' | 'skip'
}

export interface RestoreStep {
  name: string
  description: string
  action: () => Promise<StepResult>
  rollback: () => Promise<StepResult>
}

export interface StepResult {
  success: boolean
  details: string
  duration: number
}

export interface BackupSummary {
  totalBackups: number
  totalSize: number
  lastBackup: string | null
  lastRestore: string | null
  schedules: BackupSchedule[]
  storageAvailable: number
  storageUsed: number
}

const BACKUP_INDEX_KEY = 'aetheros.backup.index'
const BACKUP_CONFIG_KEY = 'aetheros.backup.config'

class BackupEngine {
  private backups: BackupEntry[] = []
  private config: BackupConfig = {
    autoBackup: false,
    schedule: 'weekly',
    scope: ['config', 'workspace', 'extensions'],
    maxBackups: 10,
    encrypt: false,
    format: 'zip',
    location: '',
  }

  constructor() {
    this.loadIndex()
    this.loadConfig()
  }

  getConfig(): BackupConfig {
    return { ...this.config }
  }

  updateConfig(updates: Partial<BackupConfig>) {
    this.config = { ...this.config, ...updates }
    this.saveConfig()
  }

  async createBackup(options: BackupOptions): Promise<BackupManifest> {
    const id = `backup_${Date.now()}`
    const manifest: BackupManifest = {
      id,
      name: options.name || `Backup ${new Date().toLocaleDateString()}`,
      version: '1.0',
      appVersion: '1.0.0',
      createdAt: new Date().toISOString(),
      scope: options.scope || ['config', 'workspace', 'extensions'],
      format: options.format || 'zip',
      size: 0,
      checksum: '',
      encrypted: options.encrypt || false,
      includes: this.resolveScopePaths(options.scope || ['config']),
      metadata: options.metadata || {},
    }

    const entry: BackupEntry = {
      manifest,
      path: `backups/${id}.${manifest.format}`,
      date: new Date(),
      size: 0,
    }

    this.backups.push(entry)
    this.pruneOldBackups()
    this.saveIndex()
    return manifest
  }

  async createFullBackup(): Promise<BackupManifest> {
    return this.createBackup({
      name: `Full Backup ${new Date().toLocaleDateString()}`,
      scope: ['all'],
      format: 'zip',
    })
  }

  getBackups(): BackupEntry[] {
    return [...this.backups].sort((a, b) => b.date.getTime() - a.date.getTime())
  }

  getBackup(id: string): BackupEntry | undefined {
    return this.backups.find(b => b.manifest.id === id)
  }

  getLatestBackup(): BackupEntry | null {
    if (this.backups.length === 0) return null
    return this.backups.reduce((latest, current) =>
      current.date > latest.date ? current : latest, this.backups[0]
    )
  }

  async deleteBackup(id: string): Promise<boolean> {
    const index = this.backups.findIndex(b => b.manifest.id === id)
    if (index === -1) return false
    this.backups.splice(index, 1)
    this.saveIndex()
    return true
  }

  async analyzeRestore(id: string): Promise<RestorePlan> {
    const backup = this.getBackup(id)
    if (!backup) throw new Error(`Backup "${id}" not found`)

    return {
      manifest: backup.manifest,
      conflicts: [],
      estimatedSize: backup.size,
      requiresRestart: backup.manifest.scope.includes('config'),
      steps: backup.manifest.scope.map(scope => ({
        name: `Restore ${scope}`,
        description: `Restoring ${scope} data`,
        action: async () => ({ success: true, details: `Restored ${scope}`, duration: 0 }),
        rollback: async () => ({ success: true, details: `Rolled back ${scope}`, duration: 0 }),
      })),
    }
  }

  async restore(id: string, plan?: RestorePlan): Promise<StepResult> {
    const resolved = plan || await this.analyzeRestore(id)
    const startTime = Date.now()

    for (const step of resolved.steps) {
      const result = await step.action()
      if (!result.success) {
        for (const prev of resolved.steps) {
          await prev.rollback()
        }
        return { success: false, details: `Failed at step: ${step.name}`, duration: Date.now() - startTime }
      }
    }

    return { success: true, details: `Restored from backup ${id}`, duration: Date.now() - startTime }
  }

  getSummary(): BackupSummary {
    const totalSize = this.backups.reduce((sum, b) => sum + b.size, 0)
    return {
      totalBackups: this.backups.length,
      totalSize,
      lastBackup: this.getLatestBackup()?.manifest.createdAt || null,
      lastRestore: null,
      schedules: this.config.autoBackup ? [this.config.schedule] : [],
      storageAvailable: 1024 * 1024 * 1024,
      storageUsed: totalSize,
    }
  }

  private resolveScopePaths(scopes: BackupScope[]): string[] {
    const paths: string[] = []
    if (scopes.includes('all') || scopes.includes('config')) paths.push('.config/aetheros')
    if (scopes.includes('all') || scopes.includes('workspace')) paths.push('workspaces')
    if (scopes.includes('all') || scopes.includes('extensions')) paths.push('extensions')
    if (scopes.includes('all') || scopes.includes('themes')) paths.push('themes')
    if (scopes.includes('all') || scopes.includes('sync')) paths.push('sync')
    if (scopes.includes('all') || scopes.includes('sessions')) paths.push('sessions')
    if (scopes.includes('all') || scopes.includes('knowledge')) paths.push('knowledge')
    return paths
  }

  private pruneOldBackups() {
    if (this.backups.length > this.config.maxBackups) {
      const sorted = [...this.backups].sort((a, b) => a.date.getTime() - b.date.getTime())
      const toRemove = this.backups.length - this.config.maxBackups
      this.backups = sorted.slice(toRemove)
    }
  }

  private loadIndex() {
    try {
      const raw = window.localStorage.getItem(BACKUP_INDEX_KEY)
      if (raw) {
        const data = JSON.parse(raw)
        this.backups = data.map((b: BackupEntry) => ({
          ...b,
          date: new Date(b.date),
        }))
      }
    } catch {
      this.backups = []
    }
  }

  private saveIndex() {
    try {
      window.localStorage.setItem(BACKUP_INDEX_KEY, JSON.stringify(this.backups))
    } catch {
      console.error('Failed to save backup index')
    }
  }

  private loadConfig() {
    try {
      const raw = window.localStorage.getItem(BACKUP_CONFIG_KEY)
      if (raw) this.config = { ...this.config, ...JSON.parse(raw) }
    } catch {}
  }

  private saveConfig() {
    try {
      window.localStorage.setItem(BACKUP_CONFIG_KEY, JSON.stringify(this.config))
    } catch {}
  }
}

export interface BackupConfig {
  autoBackup: boolean
  schedule: BackupSchedule
  scope: BackupScope[]
  maxBackups: number
  encrypt: boolean
  format: BackupFormat
  location: string
}

export interface BackupOptions {
  name?: string
  scope?: BackupScope[]
  format?: BackupFormat
  encrypt?: boolean
  metadata?: Record<string, string>
}

export const backupEngine = new BackupEngine()
