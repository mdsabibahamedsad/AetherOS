import { atom } from 'nanostores'

export type DeviceOS = 'windows' | 'macos' | 'linux' | 'ios' | 'android' | 'web'
export type DeviceSyncStatus = 'synced' | 'syncing' | 'pending' | 'error' | 'offline'

export interface DeviceInfo {
  id: string
  name: string
  os: DeviceOS
  osVersion: string
  appVersion: string
  lastActive: string
  online: boolean
  syncStatus: DeviceSyncStatus
  isCurrent: boolean
  ipAddress?: string
  location?: string
  registeredAt: string
}

export interface DevicesState {
  devices: DeviceInfo[]
  currentDevice: DeviceInfo | null
  loading: boolean
  search: string
  filterOS: DeviceOS | null
}

function detectOS(): DeviceOS {
  const platform = typeof navigator !== 'undefined' ? navigator.platform.toLowerCase() : ''

  if (platform.includes('mac')) {return 'macos'}

  if (platform.includes('linux')) {return 'linux'}

  return 'windows'
}

const CURRENT_DEVICE: DeviceInfo = {
  id: 'device-current',
  name: 'This Device',
  os: detectOS(),
  // Honest empties: no device-provenance backend is connected, so OS
  // version, app version, and IP are unknown — never invented. The view
  // renders only fields that are present.
  osVersion: '',
  appVersion: '',
  lastActive: new Date().toISOString(),
  online: true,
  // No sync engine is connected: 'offline' states the truth. It must
  // never read 'synced' without a backend confirming synchronization.
  syncStatus: 'offline',
  isCurrent: true,
  ipAddress: '',
  registeredAt: new Date().toISOString(),
}

export const $devices = atom<DeviceInfo[]>([CURRENT_DEVICE])
export const $currentDevice = atom<DeviceInfo>(CURRENT_DEVICE)
export const $deviceLoading = atom<boolean>(false)
export const $deviceSearch = atom<string>('')
export const $deviceFilterOS = atom<DeviceOS | null>(null)

export function registerDevice(device: DeviceInfo) {
  const devices = $devices.get()

  if (devices.some(d => d.id === device.id)) {return}
  $devices.set([device, ...devices])
}

export function revokeDevice(deviceId: string) {
  const current = $currentDevice.get()

  if (current.id === deviceId) {return}
  $devices.set($devices.get().filter(d => d.id !== deviceId))
}

export function renameDevice(deviceId: string, name: string) {
  $devices.set($devices.get().map(d =>
    d.id === deviceId ? { ...d, name } : d
  ))
}

export function refreshDevices() {
  $deviceLoading.set(true)
  $devices.set([...$devices.get()])
  $deviceLoading.set(false)
}

export function updateDeviceSyncStatus(deviceId: string, status: DeviceSyncStatus) {
  $devices.set($devices.get().map(d =>
    d.id === deviceId ? { ...d, syncStatus: status } : d
  ))
}

export function updateDeviceOnline(deviceId: string, online: boolean) {
  $devices.set($devices.get().map(d =>
    d.id === deviceId ? { ...d, online, lastActive: online ? new Date().toISOString() : d.lastActive } : d
  ))
}

export function setDeviceSearch(search: string) {
  $deviceSearch.set(search)
}

export function setDeviceFilterOS(os: DeviceOS | null) {
  $deviceFilterOS.set(os)
}

export function getFilteredDevices(): DeviceInfo[] {
  const search = $deviceSearch.get().toLowerCase()
  const filterOS = $deviceFilterOS.get()

  return $devices.get().filter(d => {
    if (filterOS && d.os !== filterOS) {return false}

    if (search && !d.name.toLowerCase().includes(search) && !d.id.toLowerCase().includes(search)) {return false}

    return true
  })
}

export function getDevice(id: string): DeviceInfo | undefined {
  return $devices.get().find(d => d.id === id)
}
