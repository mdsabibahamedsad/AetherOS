export type ErrorSeverity = 'info' | 'warning' | 'error' | 'critical'
export type ErrorCategory = 'crash' | 'network' | 'filesystem' | 'permission' | 'plugin' | 'update' | 'config' | 'runtime' | 'unknown'
export type ErrorSource = 'renderer' | 'main' | 'preload' | 'plugin' | 'backend' | 'native'

export interface CategorizedError {
  id: string
  message: string
  stack?: string
  severity: ErrorSeverity
  category: ErrorCategory
  source: ErrorSource
  timestamp: number
  component?: string
  context?: Record<string, string>
  recovered: boolean
  suggestion?: string
  frequency: number
}

interface ErrorPattern {
  pattern: RegExp
  category: ErrorCategory
  severity: ErrorSeverity
  suggestion?: string
}

const ERROR_PATTERNS: ErrorPattern[] = [
  { pattern: /ENOENT|ENOTDIR|EACCES|EPERM|EBUSY/, category: 'filesystem', severity: 'error', suggestion: 'Check file permissions and paths. Ensure the file exists and is accessible.' },
  { pattern: /ETIMEDOUT|ECONNREFUSED|ECONNRESET|ENETUNREACH/, category: 'network', severity: 'error', suggestion: 'Check network connectivity. Ensure the server is running and accessible.' },
  { pattern: /not found|cannot find|module.*not found/i, category: 'runtime', severity: 'error', suggestion: 'A required module or dependency is missing. Try reinstalling.' },
  { pattern: /out of memory|heap|allocation failed/i, category: 'runtime', severity: 'critical', suggestion: 'System is running low on memory. Close other applications or increase RAM.' },
  { pattern: /permission denied|not allowed|access denied/i, category: 'permission', severity: 'error', suggestion: 'You do not have permission for this operation. Check your access rights.' },
  { pattern: /update|upgrade|install.*fail/i, category: 'update', severity: 'warning', suggestion: 'Update failed. Check network connectivity and disk space.' },
  { pattern: /plugin|extension.*error|.*plugin.*fail/i, category: 'plugin', severity: 'warning', suggestion: 'A plugin encountered an error. Try disabling recently installed plugins.' },
  { pattern: /config|configuration.*invalid/i, category: 'config', severity: 'warning', suggestion: 'Configuration is invalid. Reset to defaults or check config file syntax.' },
  { pattern: /crash|segfault|sigsegv|sigabrt|fatal/i, category: 'crash', severity: 'critical', suggestion: 'The application crashed. Restart in safe mode to disable extensions.' },
  { pattern: /timeout|timed out|timedout/i, category: 'network', severity: 'warning', suggestion: 'Operation timed out. Check network speed or increase timeout settings.' },
]

export function categorizeError(error: Error, source: ErrorSource = 'unknown'): CategorizedError {
  const message = error.message || String(error)
  const stack = error.stack

  for (const pattern of ERROR_PATTERNS) {
    if (pattern.pattern.test(message)) {
      return {
        id: generateErrorId(),
        message,
        stack,
        severity: pattern.severity,
        category: pattern.category,
        source,
        timestamp: Date.now(),
        recovered: false,
        suggestion: pattern.suggestion,
        frequency: 1,
      }
    }
  }

  return {
    id: generateErrorId(),
    message,
    stack,
    severity: 'error',
    category: 'unknown',
    source,
    timestamp: Date.now(),
    recovered: false,
    suggestion: 'An unexpected error occurred. Please report this issue.',
    frequency: 1,
  }
}

export function getRecoverySuggestion(category: ErrorCategory): string {
  const suggestions: Record<ErrorCategory, string> = {
    crash: 'Restart the application. If the issue persists, run with --safe-mode to disable extensions.',
    network: 'Check your internet connection. Verify that required services are running.',
    filesystem: 'Check file permissions and ensure the path exists. Try saving to a different location.',
    permission: 'Grant the required permissions in Settings > Security. Restart the application.',
    plugin: 'Disable recently installed plugins. Check plugin compatibility with current version.',
    update: 'Check disk space and network connectivity. Try manual update from the releases page.',
    config: 'Reset configuration to defaults in Settings > Advanced. Restart the application.',
    runtime: 'Restart the application. If persistent, reinstall the application.',
    unknown: 'Please report this error with the diagnostic bundle for analysis.',
  }
  return suggestions[category] || suggestions.unknown
}

export function exportDiagnosticBundle(errors: CategorizedError[]): DiagnosticBundle {
  return {
    appVersion: '1.0.0',
    platform: navigator.platform,
    userAgent: navigator.userAgent,
    timestamp: Date.now(),
    errors: errors.map(e => ({
      id: e.id,
      message: e.message,
      severity: e.severity,
      category: e.category,
      source: e.source,
      timestamp: e.timestamp,
    })),
    errorCount: errors.length,
    categories: countByCategory(errors),
    severities: countBySeverity(errors),
  }
}

export interface DiagnosticBundle {
  appVersion: string
  platform: string
  userAgent: string
  timestamp: number
  errors: Array<{
    id: string
    message: string
    severity: ErrorSeverity
    category: ErrorCategory
    source: ErrorSource
    timestamp: number
  }>
  errorCount: number
  categories: Record<string, number>
  severities: Record<string, number>
}

function countByCategory(errors: CategorizedError[]): Record<string, number> {
  const counts: Record<string, number> = {}
  for (const e of errors) {
    counts[e.category] = (counts[e.category] ?? 0) + 1
  }
  return counts
}

function countBySeverity(errors: CategorizedError[]): Record<string, number> {
  const counts: Record<string, number> = {}
  for (const e of errors) {
    counts[e.severity] = (counts[e.severity] ?? 0) + 1
  }
  return counts
}

let errorCounter = 0
function generateErrorId(): string {
  return `err_${Date.now()}_${++errorCounter}`
}
