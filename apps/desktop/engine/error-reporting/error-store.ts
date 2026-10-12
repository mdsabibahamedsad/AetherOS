import { categorizeError, type CategorizedError, type ErrorSource, exportDiagnosticBundle, type DiagnosticBundle, getRecoverySuggestion } from './error-categorizer'

const MAX_STORED_ERRORS = 100
const ERROR_STORE_KEY = 'aetheros.error.store'

class ErrorStore {
  private errors: CategorizedError[] = []
  private listeners: Array<(errors: CategorizedError[]) => void> = []
  private errorCounts: Map<string, number> = new Map()

  constructor() {
    this.load()
  }

  report(error: Error, source: ErrorSource = 'unknown', context?: Record<string, string>): CategorizedError {
    const categorized = categorizeError(error, source)

    const existing = this.errors.find(e => e.message === categorized.message && e.category === categorized.category)
    if (existing) {
      existing.frequency++
      existing.timestamp = Date.now()
      this.save()
      this.notify()
      return existing
    }

    categorized.recovered = false
    categorized.context = context
    categorized.suggestion = getRecoverySuggestion(categorized.category)

    this.errors.unshift(categorized)
    this.errorCounts.set(categorized.category, (this.errorCounts.get(categorized.category) ?? 0) + 1)

    if (this.errors.length > MAX_STORED_ERRORS) {
      this.errors = this.errors.slice(0, MAX_STORED_ERRORS)
    }

    this.save()
    this.notify()
    return categorized
  }

  markRecovered(errorId: string) {
    const error = this.errors.find(e => e.id === errorId)
    if (error) {
      error.recovered = true
      this.save()
      this.notify()
    }
  }

  getErrors(): CategorizedError[] {
    return [...this.errors]
  }

  getErrorsByCategory(category: string): CategorizedError[] {
    return this.errors.filter(e => e.category === category)
  }

  getErrorsBySeverity(severity: string): CategorizedError[] {
    return this.errors.filter(e => e.severity === severity)
  }

  getRecentErrors(count: number = 10): CategorizedError[] {
    return this.errors.slice(0, count)
  }

  getCriticalErrors(): CategorizedError[] {
    return this.errors.filter(e => e.severity === 'critical')
  }

  getErrorCount(): number {
    return this.errors.length
  }

  getCategoryCounts(): Record<string, number> {
    const counts: Record<string, number> = {}
    for (const [key, value] of this.errorCounts) {
      counts[key] = value
    }
    return counts
  }

  getDiagnosticBundle(): DiagnosticBundle {
    return exportDiagnosticBundle(this.errors)
  }

  clearErrors() {
    this.errors = []
    this.errorCounts.clear()
    this.save()
    this.notify()
  }

  onChange(callback: (errors: CategorizedError[]) => void) {
    this.listeners.push(callback)
    callback([...this.errors])
  }

  private notify() {
    for (const listener of this.listeners) {
      listener([...this.errors])
    }
  }

  private load() {
    try {
      const raw = window.localStorage.getItem(ERROR_STORE_KEY)
      if (raw) {
        this.errors = JSON.parse(raw)
        for (const e of this.errors) {
          this.errorCounts.set(e.category, (this.errorCounts.get(e.category) ?? 0) + 1)
        }
      }
    } catch {
      this.errors = []
    }
  }

  private save() {
    try {
      window.localStorage.setItem(ERROR_STORE_KEY, JSON.stringify(this.errors))
    } catch {
      console.error('Failed to save error store')
    }
  }
}

export const errorStore = new ErrorStore()
