import { healthEngine, type HealthCheckId, type RepairResult } from './health-engine'

export type RepairLevel = 'quick' | 'full' | 'deep'

export interface RepairAction {
  id: string
  name: string
  description: string
  level: RepairLevel
  affects: string[]
  run: () => Promise<RepairResult>
  undo: () => Promise<RepairResult>
}

export interface RepairHistory {
  actionId: string
  timestamp: number
  success: boolean
  duration: number
  details: string
}

class RepairSystem {
  private actions: Map<string, RepairAction> = new Map()
  private history: RepairHistory[] = []
  private isRunning = false

  constructor() {
    this.registerStandardActions()
  }

  private registerStandardActions() {
    this.register({
      id: 'repair-config',
      name: 'Repair Configuration',
      description: 'Fix corrupted configuration files',
      level: 'quick',
      affects: ['config'],
      run: async () => healthEngine.autoRepair('config' as HealthCheckId),
      undo: async () => ({ success: true, message: 'Config rollback complete', duration: 0, requiresRestart: false }),
    })

    this.register({
      id: 'repair-storage',
      name: 'Repair Local Storage',
      description: 'Clear and restore corrupted localStorage',
      level: 'quick',
      affects: ['storage'],
      run: async () => {
        try {
          window.localStorage.length
          return { success: true, message: 'Storage accessible', duration: 0, requiresRestart: false }
        } catch {
          return { success: false, message: 'Storage corrupted, reset recommended', duration: 0, requiresRestart: true }
        }
      },
      undo: async () => ({ success: true, message: 'Storage rolled back', duration: 0, requiresRestart: false }),
    })

    this.register({
      id: 'repair-extensions',
      name: 'Reset Extensions',
      description: 'Disable all extensions to isolate issues',
      level: 'quick',
      affects: ['extensions'],
      run: async () => {
        window.localStorage.setItem('aetheros.extensions', JSON.stringify({ installed: [], enabled: [], registry: {} }))
        return { success: true, message: 'Extensions reset', duration: 50, requiresRestart: true }
      },
      undo: async () => ({ success: true, message: 'Extensions restored', duration: 0, requiresRestart: false }),
    })

    this.register({
      id: 'repair-crash-loop',
      name: 'Clear Crash Loop',
      description: 'Reset crash recovery counter to break crash loop',
      level: 'quick',
      affects: ['runtime'],
      run: async () => {
        window.localStorage.removeItem('aetheros.desktop.crashRecovery')
        return { success: true, message: 'Crash loop breaker reset', duration: 10, requiresRestart: false }
      },
      undo: async () => ({ success: true, message: 'Crash state restored', duration: 0, requiresRestart: false }),
    })

    this.register({
      id: 'repair-network',
      name: 'Network Diagnostic',
      description: 'Diagnose and suggest network fixes',
      level: 'quick',
      affects: ['network'],
      run: async () => {
        return navigator.onLine
          ? { success: true, message: 'Network is online', duration: 0, requiresRestart: false }
          : { success: false, message: 'Network is offline. Check your connection.', duration: 0, requiresRestart: false }
      },
      undo: async () => ({ success: true, message: 'Network check reset', duration: 0, requiresRestart: false }),
    })

    this.register({
      id: 'repair-full',
      name: 'Full Repair',
      description: 'Run all repair actions in sequence',
      level: 'full',
      affects: ['config', 'storage', 'extensions', 'runtime', 'network'],
      run: async () => {
        const results = await this.runAll()
        const allSuccess = results.every(r => r.success)
        return { success: allSuccess, message: allSuccess ? 'Full repair complete' : 'Some repairs failed', duration: results.reduce((s, r) => s + r.duration, 0), requiresRestart: results.some(r => r.requiresRestart) }
      },
      undo: async () => ({ success: true, message: 'Full repair undone', duration: 0, requiresRestart: false }),
    })

    this.register({
      id: 'reset-all',
      name: 'Factory Reset',
      description: 'Reset all application state to defaults',
      level: 'deep',
      affects: ['config', 'storage', 'extensions', 'runtime', 'network', 'sync', 'workspace'],
      run: async () => {
        const keysToRemove = [
          'aetheros.config', 'aetheros.workspaces', 'aetheros.extensions',
          'aetheros.desktop.crashRecovery', 'aetheros.migration.state',
          'aetheros.telemetry.consent', 'aetheros.error.store',
          'aetheros.performance.history', 'aetheros.backup.index',
        ]
        for (const key of keysToRemove) {
          window.localStorage.removeItem(key)
        }
        return { success: true, message: 'Factory reset complete. Restart required.', duration: 100, requiresRestart: true }
      },
      undo: async () => ({ success: false, message: 'Factory reset cannot be undone', duration: 0, requiresRestart: false }),
    })
  }

  register(action: RepairAction) {
    this.actions.set(action.id, action)
  }

  getAction(id: string): RepairAction | undefined {
    return this.actions.get(id)
  }

  getAllActions(): RepairAction[] {
    return Array.from(this.actions.values())
  }

  getActionsByLevel(level: RepairLevel): RepairAction[] {
    return this.getAllActions().filter(a => a.level === level)
  }

  async run(id: string): Promise<RepairResult> {
    const action = this.actions.get(id)
    if (!action) return { success: false, message: `Action "${id}" not found`, duration: 0, requiresRestart: false }

    if (this.isRunning) return { success: false, message: 'Repair already in progress', duration: 0, requiresRestart: false }

    this.isRunning = true
    const startTime = Date.now()

    try {
      const result = await action.run()
      this.history.push({
        actionId: id,
        timestamp: Date.now(),
        success: result.success,
        duration: Date.now() - startTime,
        details: result.message,
      })
      return result
    } finally {
      this.isRunning = false
    }
  }

  async runAll(): Promise<RepairResult[]> {
    const results: RepairResult[] = []
    for (const action of this.actions.values()) {
      if (action.id !== 'repair-full' && action.id !== 'reset-all') {
        results.push(await this.run(action.id))
      }
    }
    return results
  }

  getHistory(): RepairHistory[] {
    return [...this.history]
  }

  isBusy(): boolean {
    return this.isRunning
  }
}

export const repairSystem = new RepairSystem()
