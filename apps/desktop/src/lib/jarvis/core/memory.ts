interface MemoryEntry {
  id: string
  type: 'project' | 'preference' | 'coding-style' | 'workspace' | 'schedule' | 'goal' | 'pinned-task' | 'conversation' | 'model-preference' | 'fact' | 'context'
  key: string
  value: unknown
  tags: string[]
  createdAt: number
  updatedAt: number
  accessCount: number
}

const store = new Map<string, MemoryEntry>()

function key(type: MemoryEntry['type'], k: string): string {
  return `${type}::${k}`
}

export function remember(type: MemoryEntry['type'], k: string, value: unknown, tags: string[] = []): void {
  const id = key(type, k)
  const existing = store.get(id)

  if (existing) {
    store.set(id, { ...existing, value, tags, updatedAt: Date.now(), accessCount: existing.accessCount + 1 })
  } else {
    store.set(id, { id, type, key: k, value, tags, createdAt: Date.now(), updatedAt: Date.now(), accessCount: 1 })
  }
}

export function recall<T = unknown>(type: MemoryEntry['type'], k: string): T | undefined {
  const entry = store.get(key(type, k))

  if (entry) {
    entry.accessCount++

    return entry.value as T
  }

  return undefined
}

export function forget(type: MemoryEntry['type'], k: string): void {
  store.delete(key(type, k))
}

export function searchMemory(query: string, limit = 10): MemoryEntry[] {
  const q = query.toLowerCase()

  return Array.from(store.values())
    .filter(e => e.key.toLowerCase().includes(q) || e.tags.some(t => t.toLowerCase().includes(q)))
    .sort((a, b) => b.accessCount - a.accessCount)
    .slice(0, limit)
}

export function getAllMemory(): MemoryEntry[] {
  return Array.from(store.values())
}

export function getMemoryStats(): { total: number; byType: Record<string, number> } {
  const byType: Record<string, number> = {}
  store.forEach(e => { byType[e.type] = (byType[e.type] ?? 0) + 1 })

  return { total: store.size, byType }
}

export function clearMemory(): void {
  store.clear()
}

export function seedCoreMemory(): void {
  remember('preference', 'ui.theme', 'dark')
  remember('preference', 'ui.animations', true)
  remember('preference', 'voice.wake-word', 'Aether')
  remember('preference', 'autonomy.enabled', false)
  remember('preference', 'reasoning.depth', 'balanced')
  remember('fact', 'app.version', '3.0.0')
  remember('fact', 'app.name', 'AetherOS')
}
