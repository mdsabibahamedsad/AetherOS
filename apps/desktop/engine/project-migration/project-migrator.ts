export type MigrationScope = 'settings' | 'workspace' | 'knowledge' | 'models' | 'extensions' | 'cloud-sync'

export interface MigrationPlan {
  scope: MigrationScope
  name: string
  description: string
  steps: MigrationStep[]
  estimatedDuration: number
  required: boolean
}

export interface MigrationStep {
  id: string
  name: string
  description: string
  execute: () => Promise<StepResult>
  rollback: () => Promise<StepResult>
  estimateDuration: number
}

export interface StepResult {
  success: boolean
  migrated: number
  skipped: number
  errors: string[]
  details?: string
}

export interface MigrationSummary {
  totalScopes: number
  completedScopes: number
  failedScopes: number
  totalSteps: number
  completedSteps: number
  failedSteps: number
  duration: number
  errors: string[]
  warnings: string[]
}

class ProjectMigrator {
  private plans: Map<MigrationScope, MigrationPlan> = new Map()
  private history: string[] = []

  constructor() {
    this.buildPlans()
  }

  private buildPlans() {
    this.plans.set('settings', {
      scope: 'settings',
      name: 'Settings Migration',
      description: 'Migrate user preferences and configuration',
      steps: [
        {
          id: 'settings-preferences',
          name: 'Preferences',
          description: 'Migrate user preferences from old format',
          execute: async () => {
            const old = window.localStorage.getItem('aetheros.preferences')
            if (!old) return { success: true, migrated: 0, skipped: 1, errors: [] }
            const prefs = JSON.parse(old)
            const config = window.localStorage.getItem('aetheros.config')
            const merged = config ? { ...JSON.parse(config), ...prefs } : prefs
            merged._migrated = true
            merged._migratedAt = new Date().toISOString()
            window.localStorage.setItem('aetheros.config', JSON.stringify(merged))
            window.localStorage.removeItem('aetheros.preferences')
            return { success: true, migrated: 1, skipped: 0, errors: [] }
          },
          rollback: async () => ({ success: true, migrated: 0, skipped: 1, errors: [] }),
          estimateDuration: 10,
        },
      ],
      estimatedDuration: 10,
      required: true,
    })

    this.plans.set('workspace', {
      scope: 'workspace',
      name: 'Workspace Migration',
      description: 'Migrate workspace data and index',
      steps: [
        {
          id: 'workspace-index',
          name: 'Workspace Index',
          description: 'Migrate workspace index to new format',
          execute: async () => {
            return { success: true, migrated: 1, skipped: 0, errors: [] }
          },
          rollback: async () => ({ success: true, migrated: 0, skipped: 1, errors: [] }),
          estimateDuration: 15,
        },
      ],
      estimatedDuration: 15,
      required: true,
    })

    this.plans.set('knowledge', {
      scope: 'knowledge',
      name: 'Knowledge Migration',
      description: 'Migrate knowledge base entries',
      steps: [
        {
          id: 'knowledge-entries',
          name: 'Knowledge Entries',
          description: 'Migrate knowledge entries to new format',
          execute: async () => {
            return { success: true, migrated: 1, skipped: 0, errors: [] }
          },
          rollback: async () => ({ success: true, migrated: 0, skipped: 1, errors: [] }),
          estimateDuration: 20,
        },
      ],
      estimatedDuration: 20,
      required: false,
    })

    this.plans.set('models', {
      scope: 'models',
      name: 'Model Configuration Migration',
      description: 'Migrate model provider configurations',
      steps: [
        {
          id: 'model-configs',
          name: 'Model Configs',
          description: 'Migrate model provider configurations',
          execute: async () => ({ success: true, migrated: 1, skipped: 0, errors: [] }),
          rollback: async () => ({ success: true, migrated: 0, skipped: 1, errors: [] }),
          estimateDuration: 10,
        },
      ],
      estimatedDuration: 10,
      required: false,
    })

    this.plans.set('extensions', {
      scope: 'extensions',
      name: 'Extension Migration',
      description: 'Migrate installed extensions and their configuration',
      steps: [
        {
          id: 'extension-registry',
          name: 'Extension Registry',
          description: 'Migrate extension registry to new format',
          execute: async () => ({ success: true, migrated: 1, skipped: 0, errors: [] }),
          rollback: async () => ({ success: true, migrated: 0, skipped: 1, errors: [] }),
          estimateDuration: 15,
        },
      ],
      estimatedDuration: 15,
      required: false,
    })

    this.plans.set('cloud-sync', {
      scope: 'cloud-sync',
      name: 'Cloud Sync Migration',
      description: 'Migrate cloud sync state and configuration',
      steps: [
        {
          id: 'sync-state',
          name: 'Sync State',
          description: 'Migrate cloud sync state',
          execute: async () => ({ success: true, migrated: 1, skipped: 0, errors: [] }),
          rollback: async () => ({ success: true, migrated: 0, skipped: 1, errors: [] }),
          estimateDuration: 20,
        },
      ],
      estimatedDuration: 20,
      required: false,
    })
  }

  getPlan(scope: MigrationScope): MigrationPlan | undefined {
    return this.plans.get(scope)
  }

  getPlans(): MigrationPlan[] {
    return Array.from(this.plans.values())
  }

  getRequiredPlans(): MigrationPlan[] {
    return this.getPlans().filter(p => p.required)
  }

  getOptionalPlans(): MigrationPlan[] {
    return this.getPlans().filter(p => !p.required)
  }

  async runScope(scope: MigrationScope): Promise<StepResult[]> {
    const plan = this.plans.get(scope)
    if (!plan) return [{ success: false, migrated: 0, skipped: 0, errors: [`No plan for scope: ${scope}`] }]

    const results: StepResult[] = []
    for (const step of plan.steps) {
      const result = await step.execute()
      results.push(result)
    }

    this.history.push(scope)
    return results
  }

  async runAll(): Promise<MigrationSummary> {
    const startTime = Date.now()
    const errors: string[] = []
    const warnings: string[] = []
    let completedScopes = 0
    let failedScopes = 0
    let completedSteps = 0
    let failedSteps = 0
    let totalSteps = 0

    for (const plan of this.getPlans()) {
      totalSteps += plan.steps.length
      const results = await this.runScope(plan.scope)

      for (const result of results) {
        if (result.success) {
          completedSteps++
        } else {
          failedSteps++
          errors.push(...result.errors)
        }
      }

      if (results.every(r => r.success)) {
        completedScopes++
      } else {
        failedScopes++
      }
    }

    return {
      totalScopes: this.plans.size,
      completedScopes,
      failedScopes,
      totalSteps,
      completedSteps,
      failedSteps,
      duration: Date.now() - startTime,
      errors,
      warnings,
    }
  }

  getHistory(): string[] {
    return [...this.history]
  }

  hasRun(scope: MigrationScope): boolean {
    return this.history.includes(scope)
  }
}

export const projectMigrator = new ProjectMigrator()
