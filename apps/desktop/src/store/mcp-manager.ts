/**
 * MCP Manager store — MCP server lifecycle, health, and discovery.
 */
import { atom } from 'nanostores'

export type McpServerStatus = 'healthy' | 'unhealthy' | 'unknown'
export type McpServerTransport = 'stdio' | 'sse' | 'streamable-http'

export type McpServerType =
  | 'filesystem' | 'git' | 'github' | 'browser' | 'docker'
  | 'python' | 'sqlite' | 'postgres' | 'mysql' | 'redis'
  | 'slack' | 'discord' | 'telegram' | 'googledrive' | 'notion'
  | 'custom'

export interface McpServerEntry {
  id: string
  name: string
  type: McpServerType
  transport: McpServerTransport
  url: string
  command: string
  enabled: boolean
  status: McpServerStatus
  latency: number | null
  version: string
  toolsCount: number
  autoStart: boolean
  background: boolean
}

export interface McpServerLog {
  timestamp: string
  level: 'info' | 'warn' | 'error' | 'debug'
  message: string
}

export interface McpHealthResult {
  ok: boolean
  latency: number | null
  error: string | null
  tools: string[]
}

export const $mcpServers = atom<McpServerEntry[]>([])
export const $mcpServerDetail = atom<McpServerEntry | null>(null)
export const $mcpServerLogs = atom<Record<string, McpServerLog[]>>({})
export const $mcpLoading = atom<boolean>(false)
export const $mcpHealthResults = atom<Record<string, McpHealthResult>>({})
export const $mcpDiscoveryResults = atom<McpServerEntry[]>([])
export const $mcpAddModalOpen = atom<boolean>(false)

export function addServer(server: McpServerEntry) {
  const existing = $mcpServers.get().find(s => s.id === server.id)

  if (existing) {return}
  $mcpServers.set([...$mcpServers.get(), server])
}

export function removeServer(id: string) {
  $mcpServers.set($mcpServers.get().filter(s => s.id !== id))
  const logs = { ...$mcpServerLogs.get() }
  delete logs[id]
  $mcpServerLogs.set(logs)
  const health = { ...$mcpHealthResults.get() }
  delete health[id]
  $mcpHealthResults.set(health)
}

export function enableServer(id: string) {
  const servers = $mcpServers.get().map(s =>
    s.id === id ? { ...s, enabled: true } : s
  )

  $mcpServers.set(servers)
}

export function disableServer(id: string) {
  const servers = $mcpServers.get().map(s =>
    s.id === id ? { ...s, enabled: false } : s
  )

  $mcpServers.set(servers)
}

export function restartServer(id: string) {
  const servers = $mcpServers.get().map(s =>
    s.id === id ? { ...s, status: 'unknown' as McpServerStatus } : s
  )

  $mcpServers.set(servers)
}

export function healthCheck(id: string, result: McpHealthResult) {
  $mcpHealthResults.set({ ...$mcpHealthResults.get(), [id]: result })

  const servers = $mcpServers.get().map(s =>
    s.id === id
      ? { ...s, status: result.ok ? ('healthy' as McpServerStatus) : ('unhealthy' as McpServerStatus), latency: result.latency }
      : s
  )

  $mcpServers.set(servers)
}

export function refreshServers(servers: McpServerEntry[]) {
  $mcpServers.set(servers)
}

export function discoverLocal(servers: McpServerEntry[]) {
  $mcpDiscoveryResults.set(servers)
}

export function exportConfig(): string {
  return JSON.stringify($mcpServers.get(), null, 2)
}

export function importConfig(json: string) {
  try {
    const servers: McpServerEntry[] = JSON.parse(json)
    $mcpServers.set(servers)
  } catch {
    // silent — caller handles parse errors
  }
}

export function clearLogs(id: string) {
  const logs = { ...$mcpServerLogs.get() }
  logs[id] = []
  $mcpServerLogs.set(logs)
}

export function appendLog(id: string, entry: McpServerLog) {
  const logs = { ...$mcpServerLogs.get() }
  const existing = logs[id] ?? []
  logs[id] = [...existing, entry].slice(-500)
  $mcpServerLogs.set(logs)
}

export function setMcpServerDetail(server: McpServerEntry | null) {
  $mcpServerDetail.set(server)
}

export function setMcpAddModalOpen(open: boolean) {
  $mcpAddModalOpen.set(open)
}
