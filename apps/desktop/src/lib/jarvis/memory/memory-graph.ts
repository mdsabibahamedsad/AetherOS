import type { MemoryNode, MemoryRelation } from '../types'

// ─── In-Memory Knowledge Graph ────────────────────────────────────────────────

const nodes = new Map<string, MemoryNode>()
const edges: MemoryRelation[] = []

// ─── CRUD Operations ──────────────────────────────────────────────────────────

export function createMemory(config: {
  type: MemoryNode['type']
  label: string
  content: string
  metadata?: Record<string, unknown>
}): MemoryNode {
  const node: MemoryNode = {
    id: `mem-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    type: config.type,
    label: config.label,
    content: config.content,
    metadata: config.metadata ?? {},
    relations: [],
    createdAt: Date.now(),
    updatedAt: Date.now()
  }

  nodes.set(node.id, node)

  return node
}

export function updateMemory(id: string, updates: Partial<Pick<MemoryNode, 'content' | 'metadata' | 'label'>>) {
  const node = nodes.get(id)

  if (!node) {return null}

  if (updates.content !== undefined) {node.content = updates.content}

  if (updates.metadata !== undefined) {node.metadata = { ...node.metadata, ...updates.metadata }}

  if (updates.label !== undefined) {node.label = updates.label}
  node.updatedAt = Date.now()

  return node
}

export function deleteMemory(id: string): boolean {
  const deleted = nodes.delete(id)

  // Remove related edges
  for (let i = edges.length - 1; i >= 0; i--) {
    if (edges[i].targetId === id) {edges.splice(i, 1)}
  }

  // Remove relations from other nodes
  for (const node of nodes.values()) {
    node.relations = node.relations.filter(r => r.targetId !== id)
  }

  return deleted
}

export function getMemory(id: string): MemoryNode | undefined {
  return nodes.get(id)
}

export function listMemories(type?: MemoryNode['type']): MemoryNode[] {
  const all = Array.from(nodes.values())

  return type ? all.filter(n => n.type === type) : all
}

// ─── Relations ────────────────────────────────────────────────────────────────

export function addRelation(sourceId: string, targetId: string, type: MemoryRelation['type'], weight = 1) {
  const source = nodes.get(sourceId)

  if (!source) {return}

  // Check if relation already exists
  const existing = source.relations.find(r => r.targetId === targetId && r.type === type)

  if (existing) {
    existing.weight = Math.min(5, existing.weight + 0.5)

    return
  }

  source.relations.push({ targetId, type, weight })
}

export function removeRelation(sourceId: string, targetId: string, type?: MemoryRelation['type']) {
  const source = nodes.get(sourceId)

  if (!source) {return}

  source.relations = source.relations.filter(r =>
    r.targetId !== targetId || (type && r.type !== type)
  )
}

export function getRelatedNodes(id: string): MemoryNode[] {
  const node = nodes.get(id)

  if (!node) {return []}

  return node.relations
    .map(r => nodes.get(r.targetId))
    .filter((n): n is MemoryNode => n !== undefined)
    .sort((a, b) => {
      const relA = node.relations.find(r => r.targetId === a.id)
      const relB = node.relations.find(r => r.targetId === b.id)

      return (relB?.weight ?? 0) - (relA?.weight ?? 0)
    })
}

// ─── Semantic Search ──────────────────────────────────────────────────────────

export function searchMemory(query: string, limit = 10): MemoryNode[] {
  const lower = query.toLowerCase()
  const words = lower.split(/\s+/).filter(w => w.length > 2)

  const scored = Array.from(nodes.values()).map(node => {
    let score = 0
    const text = `${node.label} ${node.content} ${Object.values(node.metadata).join(' ')}`.toLowerCase()

    // Exact match
    if (text.includes(lower)) {score += 10}

    // Word matches
    for (const word of words) {
      if (text.includes(word)) {score += 3}

      if (node.label.toLowerCase().includes(word)) {score += 5}
    }

    // Type relevance
    if (node.type === 'knowledge') {score += 2}

    if (node.type === 'project') {score += 1}

    // Recency bonus
    const age = Date.now() - node.updatedAt

    if (age < 3600000) {score += 3} // < 1 hour
    else if (age < 86400000) {score += 1} // < 1 day

    return { node, score }
  })

  return scored
    .filter(s => s.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit)
    .map(s => s.node)
}

// ─── Graph Analytics ──────────────────────────────────────────────────────────

export function getMemoryStats() {
  const all = Array.from(nodes.values())

  return {
    total: all.length,
    byType: all.reduce((acc, n) => {
      acc[n.type] = (acc[n.type] ?? 0) + 1

      return acc
    }, {} as Record<string, number>),
    totalRelations: all.reduce((sum, n) => sum + n.relations.length, 0),
    mostConnected: all
      .sort((a, b) => b.relations.length - a.relations.length)
      .slice(0, 5)
      .map(n => ({ id: n.id, label: n.label, connections: n.relations.length }))
  }
}

export function findPath(sourceId: string, targetId: string, maxDepth = 5): MemoryNode[] | null {
  if (sourceId === targetId) {
    const node = nodes.get(sourceId)

    return node ? [node] : null
  }

  const visited = new Set<string>()
  const queue: { id: string; path: MemoryNode[] }[] = []

  const startNode = nodes.get(sourceId)

  if (!startNode) {return null}
  queue.push({ id: sourceId, path: [startNode] })
  visited.add(sourceId)

  while (queue.length > 0) {
    const { id, path } = queue.shift()!

    if (path.length > maxDepth) {continue}

    const node = nodes.get(id)

    if (!node) {continue}

    for (const rel of node.relations) {
      if (rel.targetId === targetId) {
        const targetNode = nodes.get(targetId)

        if (targetNode) {return [...path, targetNode]}
      }

      if (!visited.has(rel.targetId)) {
        visited.add(rel.targetId)
        const nextNode = nodes.get(rel.targetId)

        if (nextNode) {
          queue.push({ id: rel.targetId, path: [...path, nextNode] })
        }
      }
    }
  }

  return null
}

// ─── Seed Data ────────────────────────────────────────────────────────────────

export function seedMemoryGraph() {
  const project = createMemory({ type: 'project', label: 'AetherOS', content: 'AI Operating System with desktop app, CLI, TUI, and gateway' })
  const user = createMemory({ type: 'person', label: 'User', content: 'Primary developer working on AetherOS' })
  const pref = createMemory({ type: 'preference', label: 'Dark Mode', content: 'User prefers dark theme with blue/cyan accents' })
  const codebase = createMemory({ type: 'codebase', label: 'Desktop App', content: 'Electron + React + TypeScript frontend with Python backend' })

  addRelation(project.id, user.id, 'authored-by', 3)
  addRelation(project.id, codebase.id, 'contains', 5)
  addRelation(user.id, pref.id, 'related', 2)
  addRelation(codebase.id, project.id, 'belongs-to', 5)
}
