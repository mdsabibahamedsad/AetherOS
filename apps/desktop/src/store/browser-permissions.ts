import { atom } from 'nanostores'

export type BrowserPermissionType =
  | 'read_page' | 'access_domain' | 'use_cookies' | 'download_files'
  | 'upload_files' | 'fill_forms' | 'submit_forms' | 'access_clipboard'
  | 'open_popups' | 'use_camera' | 'use_microphone' | 'control_browser'
  | 'control_desktop' | 'external_communication' | 'sensitive_website'
  | 'navigate' | 'execute_js' | 'screenshot'

export interface BrowserPermissionRequest {
  id: string
  permissionType: BrowserPermissionType
  url: string
  reason: string
  timestamp: string
  status: 'pending' | 'granted' | 'denied'
}

export interface BrowserPermissionGrant {
  permissionType: BrowserPermissionType
  url: string
  granted: boolean
  duration: 'once' | 'session' | 'permanent'
  grantedAt: string
}

export interface BrowserPermissionsState {
  pendingRequests: BrowserPermissionRequest[]
  grants: BrowserPermissionGrant[]
  domainBlocklist: string[]
  computerUseEnabled: boolean
}

export const $browserPermissions = atom<BrowserPermissionsState>({
  pendingRequests: [],
  grants: [],
  domainBlocklist: [],
  computerUseEnabled: false,
})

export function addPermissionRequest(
  permissionType: BrowserPermissionType,
  url: string,
  reason: string
) {
  const state = $browserPermissions.get()

  const req: BrowserPermissionRequest = {
    id: `perm_${Date.now()}`,
    permissionType,
    url,
    reason,
    timestamp: new Date().toISOString(),
    status: 'pending',
  }

  $browserPermissions.set({ ...state, pendingRequests: [...state.pendingRequests, req] })
}

export function grantPermission(requestId: string, duration: 'once' | 'session' | 'permanent' = 'once') {
  const state = $browserPermissions.get()
  const req = state.pendingRequests.find(r => r.id === requestId)

  if (!req) {return}

  const grant: BrowserPermissionGrant = {
    permissionType: req.permissionType,
    url: req.url,
    granted: true,
    duration,
    grantedAt: new Date().toISOString(),
  }

  $browserPermissions.set({
    ...state,
    pendingRequests: state.pendingRequests.filter(r => r.id !== requestId),
    grants: [...state.grants, grant],
  })
}

export function denyPermission(requestId: string) {
  const state = $browserPermissions.get()
  $browserPermissions.set({
    ...state,
    pendingRequests: state.pendingRequests.map(r =>
      r.id === requestId ? { ...r, status: 'denied' as const } : r
    ),
  })
}

export function blockDomain(domain: string) {
  const state = $browserPermissions.get()

  if (!state.domainBlocklist.includes(domain)) {
    $browserPermissions.set({ ...state, domainBlocklist: [...state.domainBlocklist, domain] })
  }
}

export function unblockDomain(domain: string) {
  const state = $browserPermissions.get()
  $browserPermissions.set({ ...state, domainBlocklist: state.domainBlocklist.filter(d => d !== domain) })
}

export function setComputerUseEnabled(enabled: boolean) {
  const state = $browserPermissions.get()
  $browserPermissions.set({ ...state, computerUseEnabled: enabled })
}

export function clearSessionGrants() {
  const state = $browserPermissions.get()
  $browserPermissions.set({
    ...state,
    grants: state.grants.filter(g => g.duration === 'permanent'),
  })
}
