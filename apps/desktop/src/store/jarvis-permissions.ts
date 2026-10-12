import { atom } from 'nanostores'

import type { CapabilityPermission } from '@/lib/jarvis/capabilities/registry'
import { DEFAULT_POLICY, type PermissionPolicy, type PermissionRule, sanitizePolicy } from '@/lib/jarvis/permissions/policy'

const STORAGE_KEY = 'aetheros.jarvis.permission-policy.v1'

function load(): PermissionPolicy {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)

    if (!raw) {return { ...DEFAULT_POLICY }}

    return sanitizePolicy(JSON.parse(raw) as Partial<PermissionPolicy>)
  } catch {
    return { ...DEFAULT_POLICY }
  }
}

export const $permissionPolicy = atom<PermissionPolicy>(load())

export function setPermissionRule(permission: CapabilityPermission, rule: PermissionRule) {
  const next = sanitizePolicy({ ...$permissionPolicy.get(), [permission]: rule })
  $permissionPolicy.set(next)

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  } catch {
    // Storage unavailable (private mode, etc.) — policy still holds in memory.
  }
}

/** Permissions approved for the current session only. Cleared on reload. */
export const $sessionGrants = atom<Set<CapabilityPermission>>(new Set())

export function grantSessionPermission(permission: CapabilityPermission) {
  $sessionGrants.set(new Set($sessionGrants.get()).add(permission))
}

export function clearSessionGrants() {
  $sessionGrants.set(new Set())
}
