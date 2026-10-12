/**
 * Recoverable task persistence.
 *
 * Persists minimal task metadata (no secrets, no full transcripts) so a
 * restart can restore state and honestly mark tasks interrupted vs
 * recoverable. Never claims a task continued if the process died.
 */

import type { JarvisTask, JarvisTaskStatus } from './task-state-machine'
import { forceTransition } from './task-state-machine'

const KEY = 'aetheros.jarvis.tasks.v1'
const MAX_STORED = 50

interface StoredTask {
  id: string
  input: JarvisTask['input']
  status: JarvisTaskStatus
  toolsUsed: string[]
  startedAt: number
  updatedAt: number
  completedAt?: number
  resultText: string | null
  errorMessage: string | null
}

function isBrowser(): boolean {
  return typeof localStorage !== 'undefined'
}

export function persistTask(task: JarvisTask): void {
  if (!isBrowser()) return
  try {
    const raw = localStorage.getItem(KEY)
    const list: StoredTask[] = raw ? (JSON.parse(raw) as StoredTask[]) : []
    const entry: StoredTask = {
      id: task.id,
      input: task.input,
      status: task.status,
      toolsUsed: [...task.toolsUsed],
      startedAt: task.startedAt,
      updatedAt: task.updatedAt,
      completedAt: task.completedAt,
      resultText: task.result?.text.slice(0, 500) ?? null,
      errorMessage: task.error?.message.slice(0, 500) ?? null
    }
    const next = [entry, ...list.filter(t => t.id !== task.id)].slice(0, MAX_STORED)
    localStorage.setItem(KEY, JSON.stringify(next))
  } catch { /* private mode — memory only */ }
}

export interface RecoveredTask extends StoredTask {
  recoveredAs: 'interrupted' | 'completed' | 'failed'
}

/** Restore metadata after restart. Active states → interrupted. */
export function recoverTasks(): RecoveredTask[] {
  if (!isBrowser()) return []
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return []
    const list = JSON.parse(raw) as StoredTask[]
    return list.map(t => {
      const active = !['completed', 'failed', 'cancelled', 'timed_out'].includes(t.status)
      return { ...t, recoveredAs: active ? 'interrupted' : t.status === 'completed' ? 'completed' : 'failed' }
    })
  } catch {
    return []
  }
}

export function rehydrateTask(stored: StoredTask): JarvisTask {
  const task: JarvisTask = {
    id: stored.id,
    sessionId: null,
    input: stored.input,
    status: 'queued',
    plan: [],
    toolsUsed: [...stored.toolsUsed],
    startedAt: stored.startedAt,
    updatedAt: Date.now()
  }
  void forceTransition
  if (stored.status === 'completed') forceTransition(task, 'completed')
  else if (stored.status === 'failed' || stored.status === 'timed_out') forceTransition(task, 'failed')
  else forceTransition(task, 'cancelled')
  return task
}

export function clearStoredTasks(): void {
  if (!isBrowser()) return
  try { localStorage.removeItem(KEY) } catch { /* noop */ }
}
