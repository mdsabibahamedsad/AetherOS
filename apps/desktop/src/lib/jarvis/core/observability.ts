/**
 * Jarvis observability: latency breakdown + task diagnostics.
 * No credentials or secrets are ever recorded — summaries only.
 */

export interface LatencyBreakdown {
  intentMs: number
  planningMs: number
  toolMs: number
  modelMs: number
  sttMs: number
  ttsMs: number
  totalMs: number
}

export interface TaskDiagnostic {
  taskId: string
  inputType: string
  model: string | null
  planSteps: number
  tools: string[]
  latency: LatencyBreakdown
  retries: number
  failures: string[]
  approvals: number
  result: string | null
  createdAt: number
}

const diagnostics: TaskDiagnostic[] = []
const MAX = 100

class Timer {
  private marks = new Map<string, number>()
  mark(name: string): void { this.marks.set(name, performance.now()) }
  span(from: string, to: string): number {
    const a = this.marks.get(from)
    const b = this.marks.get(to)
    if (a === undefined || b === undefined) return 0
    return Math.max(0, Math.round(b - a))
  }
}

export function createTimer(): Timer { return new Timer() }

export function recordDiagnostic(d: TaskDiagnostic): void {
  diagnostics.unshift(d)
  if (diagnostics.length > MAX) diagnostics.length = MAX
}

export function recentDiagnostics(limit = 20): TaskDiagnostic[] {
  return diagnostics.slice(0, limit)
}

export function clearDiagnostics(): void {
  diagnostics.length = 0
}
