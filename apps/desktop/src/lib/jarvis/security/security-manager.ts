import { addJarvisNotification } from '@/store/jarvis-mode'

import type { PermissionScope, SecurityPolicy } from '../types'

// ─── Security Policy ──────────────────────────────────────────────────────────

let policy: SecurityPolicy = {
  requireApproval: ['filesystem', 'terminal', 'database', 'network'],
  autoApprove: ['browser', 'camera', 'microphone'],
  deniedActions: []
}

export function getSecurityPolicy(): SecurityPolicy {
  return { ...policy }
}

export function updateSecurityPolicy(updates: Partial<SecurityPolicy>) {
  policy = { ...policy, ...updates }
}

// ─── Permission Requests ──────────────────────────────────────────────────────

export interface PermissionRequest {
  id: string
  scope: PermissionScope
  action: string
  resource: string
  agentId?: string
  timestamp: number
  status: 'pending' | 'approved' | 'denied'
  resolver?: (approved: boolean) => void
}

const pendingRequests = new Map<string, PermissionRequest>()
let requestCounter = 0

export function requestPermission(
  scope: PermissionScope,
  action: string,
  resource: string,
  agentId?: string
): Promise<boolean> {
  // Check if auto-approved
  if (policy.autoApprove.includes(scope)) {
    return Promise.resolve(true)
  }

  // Check if denied
  if (policy.deniedActions.includes(action)) {
    addJarvisNotification({
      title: 'Permission Denied',
      message: `${action} on ${resource} is denied by policy`,
      type: 'error'
    })

    return Promise.resolve(false)
  }

  // Check if approval required
  if (policy.requireApproval.includes(scope)) {
    return new Promise(resolve => {
      const request: PermissionRequest = {
        id: `perm-${++requestCounter}`,
        scope,
        action,
        resource,
        agentId,
        timestamp: Date.now(),
        status: 'pending',
        resolver: resolve
      }

      pendingRequests.set(request.id, request)

      addJarvisNotification({
        title: 'Permission Required',
        message: `${action} on ${resource} (${scope})`,
        type: 'warning'
      })
    })
  }

  return Promise.resolve(true)
}

export function approvePermission(requestId: string) {
  const request = pendingRequests.get(requestId)

  if (!request) {return}

  request.status = 'approved'
  request.resolver?.(true)
  pendingRequests.delete(requestId)
}

export function denyPermission(requestId: string) {
  const request = pendingRequests.get(requestId)

  if (!request) {return}

  request.status = 'denied'
  request.resolver?.(false)
  pendingRequests.delete(requestId)
}

export function getPendingRequests(): PermissionRequest[] {
  return Array.from(pendingRequests.values())
}

// ─── Audit Log ────────────────────────────────────────────────────────────────

export interface AuditEntry {
  timestamp: number
  scope: PermissionScope
  action: string
  resource: string
  approved: boolean
  agentId?: string
}

const auditLog: AuditEntry[] = []

export function logAction(scope: PermissionScope, action: string, resource: string, approved: boolean, agentId?: string) {
  auditLog.push({
    timestamp: Date.now(),
    scope,
    action,
    resource,
    approved,
    agentId
  })

  // Keep last 500 entries
  if (auditLog.length > 500) {
    auditLog.splice(0, auditLog.length - 500)
  }
}

export function getAuditLog(limit = 50): AuditEntry[] {
  return auditLog.slice(-limit)
}
