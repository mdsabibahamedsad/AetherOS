/**
 * Plugin Manager store — installed plugin CRUD, enable/disable, permissions, updates.
 */
import { atom } from 'nanostores'

export type PluginPermissionMode = 'allow' | 'deny' | 'ask'

export interface PluginPermission {
  resource: string
  mode: PluginPermissionMode
}

export interface InstalledPlugin {
  id: string
  name: string
  version: string
  author: string
  description: string
  icon: string
  enabled: boolean
  permissions: PluginPermission[]
  installedAt: string
  updatedAt: string
  path: string
  hasUpdate: boolean
  latestVersion: string
  categories: string[]
}

export interface PluginUpdate {
  pluginId: string
  currentVersion: string
  latestVersion: string
  changelog: string
  size: number
}

export type PluginFilter = 'all' | 'enabled' | 'disabled' | 'updates'

export const $installedPlugins = atom<InstalledPlugin[]>([])
export const $pluginLoading = atom<boolean>(false)
export const $pluginSearch = atom<string>('')
export const $pluginFilter = atom<PluginFilter>('all')
export const $availableUpdates = atom<PluginUpdate[]>([])
export const $pluginPermissions = atom<PluginPermission[]>([])
export const $pluginDetail = atom<InstalledPlugin | null>(null)

export function installPlugin(plugin: InstalledPlugin) {
  const existing = $installedPlugins.get().find(p => p.id === plugin.id)

  if (existing) {return}
  $installedPlugins.set([...$installedPlugins.get(), plugin])
}

export function uninstallPlugin(id: string) {
  $installedPlugins.set($installedPlugins.get().filter(p => p.id !== id))
  $availableUpdates.set($availableUpdates.get().filter(u => u.pluginId !== id))
}

export function enablePlugin(id: string) {
  const plugins = $installedPlugins.get().map(p =>
    p.id === id ? { ...p, enabled: true } : p
  )

  $installedPlugins.set(plugins)
}

export function disablePlugin(id: string) {
  const plugins = $installedPlugins.get().map(p =>
    p.id === id ? { ...p, enabled: false } : p
  )

  $installedPlugins.set(plugins)
}

export function updatePlugin(id: string, version: string) {
  const plugins = $installedPlugins.get().map(p =>
    p.id === id ? { ...p, version, hasUpdate: false, latestVersion: version, updatedAt: new Date().toISOString() } : p
  )

  $installedPlugins.set(plugins)
  $availableUpdates.set($availableUpdates.get().filter(u => u.pluginId !== id))
}

export function rollbackPlugin(id: string, version: string) {
  const plugins = $installedPlugins.get().map(p =>
    p.id === id ? { ...p, version, hasUpdate: true, updatedAt: new Date().toISOString() } : p
  )

  $installedPlugins.set(plugins)
}

export function refreshPlugins(plugins: InstalledPlugin[]) {
  $installedPlugins.set(plugins)
}

export function refreshUpdates(updates: PluginUpdate[]) {
  $availableUpdates.set(updates)
}

export function setPluginSearch(query: string) {
  $pluginSearch.set(query)
}

export function setPluginFilter(filter: PluginFilter) {
  $pluginFilter.set(filter)
}

export function setPluginDetail(plugin: InstalledPlugin | null) {
  $pluginDetail.set(plugin)
}

export function setPluginPermissions(permissions: PluginPermission[]) {
  $pluginPermissions.set(permissions)
}
