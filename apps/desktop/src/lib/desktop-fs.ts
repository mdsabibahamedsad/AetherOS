import type { AetherosConnection, AetherosReadDirResult, AetherosReadFileTextResult, AetherosSelectPathsOptions } from '@/global'
import { $connection } from '@/store/session'

export interface DesktopFsRemotePicker {
  selectPaths: (options?: AetherosSelectPathsOptions) => Promise<string[]>
}

let remotePicker: DesktopFsRemotePicker | null = null

export function setDesktopFsRemotePicker(next: DesktopFsRemotePicker | null) {
  remotePicker = next
}

function connectionCacheKey(connection: AetherosConnection | null) {
  if (!connection) {
    return 'local:'
  }

  return `${connection.mode || 'local'}:${connection.profile || ''}:${connection.baseUrl || ''}`
}

export function desktopFsCacheKey() {
  return connectionCacheKey($connection.get())
}

export function isDesktopFsRemoteMode() {
  return $connection.get()?.mode === 'remote'
}

function fsPath(endpoint: string, filePath: string) {
  return `/api/fs/${endpoint}?path=${encodeURIComponent(filePath)}`
}

function bridge() {
  const desktop = window.aetherosDesktop

  if (!desktop) {
    throw new Error('Aetheros Desktop bridge is unavailable')
  }

  return desktop
}

export async function readDesktopDir(path: string): Promise<AetherosReadDirResult> {
  const desktop = bridge()

  if (!isDesktopFsRemoteMode()) {
    return desktop.readDir(path)
  }

  return desktop.api<AetherosReadDirResult>({ path: fsPath('list', path) })
}

export async function readDesktopFileText(path: string): Promise<AetherosReadFileTextResult> {
  const desktop = bridge()

  if (!isDesktopFsRemoteMode()) {
    return desktop.readFileText(path)
  }

  return desktop.api<AetherosReadFileTextResult>({ path: fsPath('read-text', path) })
}

export async function readDesktopFileDataUrl(path: string): Promise<string> {
  const desktop = bridge()

  if (!isDesktopFsRemoteMode()) {
    return desktop.readFileDataUrl(path)
  }

  const result = await desktop.api<string | { dataUrl?: string }>({ path: fsPath('read-data-url', path) })

  return typeof result === 'string' ? result : result.dataUrl || ''
}

export async function desktopGitRoot(path: string): Promise<string | null> {
  const desktop = bridge()

  if (!isDesktopFsRemoteMode()) {
    return desktop.gitRoot ? desktop.gitRoot(path) : null
  }

  const result = await desktop.api<{ root: string | null }>({ path: fsPath('git-root', path) })

  return result.root
}

export async function desktopDefaultCwd(): Promise<{ branch: string; cwd: string } | null> {
  if (!isDesktopFsRemoteMode()) {
    return null
  }

  return bridge().api<{ branch: string; cwd: string }>({ path: '/api/fs/default-cwd' })
}

export async function selectDesktopPaths(options?: AetherosSelectPathsOptions): Promise<string[]> {
  const desktop = bridge()

  if (!isDesktopFsRemoteMode()) {
    return desktop.selectPaths(options)
  }

  if (!options?.directories || options.multiple !== false) {
    return []
  }

  return remotePicker ? remotePicker.selectPaths(options) : []
}
