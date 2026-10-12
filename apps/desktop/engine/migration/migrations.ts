import { migrationEngine } from './migration-engine'

export function registerStandardMigrations() {
  migrationEngine.registerMany([
    {
      id: 'config-v1-to-v2',
      name: 'Config Format v1 → v2',
      type: 'config',
      version: '1.0.0',
      description: 'Migrate flat configuration to namespaced format',
      apply: async () => {
        const raw = window.localStorage.getItem('aetheros.config')
        if (!raw) return { success: true, applied: 0, rolledBack: 0, errors: [], warnings: ['No config to migrate'], duration: 0 }
        const config = JSON.parse(raw)
        if (config._formatVersion === 2) return { success: true, applied: 0, rolledBack: 0, errors: [], warnings: [], duration: 0 }
        const migrated = { ...config, _formatVersion: 2 }
        if (typeof config.theme === 'string') {
          migrated.general = { ...(migrated.general ?? {}), theme: config.theme }
          delete migrated.theme
        }
        window.localStorage.setItem('aetheros.config', JSON.stringify(migrated))
        return { success: true, applied: 1, rolledBack: 0, errors: [], warnings: [], duration: 50 }
      },
      rollback: async () => {
        const raw = window.localStorage.getItem('aetheros.config')
        if (!raw) return { success: true, applied: 0, rolledBack: 0, errors: [], warnings: [], duration: 0 }
        const config = JSON.parse(raw)
        const restored = { ...config }
        if (restored.general && typeof restored.general === 'object') {
          const g = restored.general as Record<string, unknown>
          if (g.theme) restored.theme = g.theme
          delete restored.general
        }
        restored._formatVersion = 1
        window.localStorage.setItem('aetheros.config', JSON.stringify(restored))
        return { success: true, applied: 0, rolledBack: 1, errors: [], warnings: [], duration: 50 }
      },
      validate: async () => ({ valid: true, errors: [], warnings: [] }),
      backup: async () => {
        const raw = window.localStorage.getItem('aetheros.config')
        if (raw) {
          window.localStorage.setItem('aetheros.config.backup.v1', raw)
        }
      },
    },
    {
      id: 'workspace-index-v1',
      name: 'Workspace Index Initialization',
      type: 'workspace',
      version: '1.0.0',
      description: 'Initialize workspace index for workspace manager',
      apply: async () => {
        const existing = window.localStorage.getItem('aetheros.workspaces')
        if (existing) return { success: true, applied: 0, rolledBack: 0, errors: [], warnings: ['Workspace index already exists'], duration: 0 }
        const defaultWorkspaces = {
          workspaces: [],
          defaultLocation: '',
          lastOpened: null,
          recent: [],
        }
        window.localStorage.setItem('aetheros.workspaces', JSON.stringify(defaultWorkspaces))
        return { success: true, applied: 1, rolledBack: 0, errors: [], warnings: [], duration: 30 }
      },
      rollback: async () => {
        window.localStorage.removeItem('aetheros.workspaces')
        return { success: true, applied: 0, rolledBack: 1, errors: [], warnings: [], duration: 10 }
      },
      validate: async () => ({ valid: true, errors: [], warnings: [] }),
      backup: async () => {},
    },
    {
      id: 'knowledge-base-init',
      name: 'Knowledge Base Initialization',
      type: 'knowledge',
      version: '1.0.0',
      description: 'Initialize local knowledge base structure',
      apply: async () => {
        const existing = window.localStorage.getItem('aetheros.knowledge')
        if (existing) return { success: true, applied: 0, rolledBack: 0, errors: [], warnings: ['Knowledge base already exists'], duration: 0 }
        window.localStorage.setItem('aetheros.knowledge', JSON.stringify({ entries: [], categories: [], lastSync: null }))
        return { success: true, applied: 1, rolledBack: 0, errors: [], warnings: [], duration: 30 }
      },
      rollback: async () => {
        window.localStorage.removeItem('aetheros.knowledge')
        return { success: true, applied: 0, rolledBack: 1, errors: [], warnings: [], duration: 10 }
      },
      validate: async () => ({ valid: true, errors: [], warnings: [] }),
      backup: async () => {},
    },
    {
      id: 'extension-registry-init',
      name: 'Extension Registry Initialization',
      type: 'extensions',
      version: '1.0.0',
      description: 'Initialize extension registry for installed extensions',
      dependsOn: ['config-v1-to-v2'],
      apply: async () => {
        const existing = window.localStorage.getItem('aetheros.extensions')
        if (existing) return { success: true, applied: 0, rolledBack: 0, errors: [], warnings: [], duration: 0 }
        window.localStorage.setItem('aetheros.extensions', JSON.stringify({ installed: [], enabled: [], registry: {} }))
        return { success: true, applied: 1, rolledBack: 0, errors: [], warnings: [], duration: 30 }
      },
      rollback: async () => {
        window.localStorage.removeItem('aetheros.extensions')
        return { success: true, applied: 0, rolledBack: 1, errors: [], warnings: [], duration: 10 }
      },
      validate: async () => ({ valid: true, errors: [], warnings: [] }),
      backup: async () => {},
    },
    {
      id: 'telemetry-prefs-init',
      name: 'Telemetry Preferences',
      type: 'config',
      version: '1.0.0',
      description: 'Initialize telemetry consent state',
      dependsOn: ['config-v1-to-v2'],
      apply: async () => {
        const raw = window.localStorage.getItem('aetheros.config')
        const config = raw ? JSON.parse(raw) : {}
        config.telemetry = { enabled: false, crashReporting: false, performanceMetrics: false, consented: false }
        window.localStorage.setItem('aetheros.config', JSON.stringify(config))
        return { success: true, applied: 1, rolledBack: 0, errors: [], warnings: [], duration: 20 }
      },
      rollback: async () => {
        const raw = window.localStorage.getItem('aetheros.config')
        if (raw) {
          const config = JSON.parse(raw)
          delete config.telemetry
          window.localStorage.setItem('aetheros.config', JSON.stringify(config))
        }
        return { success: true, applied: 0, rolledBack: 1, errors: [], warnings: [], duration: 20 }
      },
      validate: async () => ({ valid: true, errors: [], warnings: [] }),
      backup: async () => {},
    },
  ])
}

export function initMigrations() {
  registerStandardMigrations()
}
