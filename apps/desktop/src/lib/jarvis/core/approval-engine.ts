/**
 * Centralized Jarvis approval engine.
 *
 * Single choke point for every privileged action. Levels:
 * NONE < LOW < MEDIUM < HIGH < CRITICAL.
 * Voice input follows the identical rule — no bypass branch exists.
 */

import { addJarvisNotification } from '@/store/jarvis-mode'

import { type Capability, type CapabilityRisk } from '../capabilities/registry'

export type ApprovalLevel = 'NONE' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'

export interface ApprovalTicket {
  id: string
  capabilityId: string
  summary: string
  detail: string | null
  level: ApprovalLevel
  inputType: 'text' | 'voice'
  createdAt: number
  decided: boolean | null
  resolver?: (approved: boolean) => void
}

const tickets = new Map<string, ApprovalTicket>()
let counter = 0

const RISK_TO_LEVEL: Record<CapabilityRisk, ApprovalLevel> = {
  low: 'LOW',
  medium: 'MEDIUM',
  high: 'HIGH',
  critical: 'CRITICAL'
}

export function levelForCapability(cap: Capability): ApprovalLevel {
  if (cap.permissions.length === 0) return 'NONE'
  return RISK_TO_LEVEL[cap.riskLevel]
}

/** Static level for destructive local phrasing (delete N files, format, send). */
export function levelForDestructiveInput(input: string): ApprovalLevel {
  if (/\bformat\b|\bwipe\b|\bdestroy\b/i.test(input)) return 'CRITICAL'
  if (/\bdelete\b|\bremove\b|\brm\s+-rf?\b|\bsend\b.*\b(email|message)\b|\bpublish\b/i.test(input)) return 'HIGH'
  return 'MEDIUM'
}

export function requestApproval(args: {
  capabilityId: string
  summary: string
  detail?: string | null
  level: ApprovalLevel
  inputType: 'text' | 'voice'
}): Promise<boolean> {
  // NONE auto-passes without a ticket.
  if (args.level === 'NONE') return Promise.resolve(true)
  const id = `apr_${Date.now().toString(36)}_${++counter}`
  return new Promise(resolve => {
    const ticket: ApprovalTicket = {
      id,
      capabilityId: args.capabilityId,
      summary: args.summary,
      detail: args.detail ?? null,
      level: args.level,
      inputType: args.inputType,
      createdAt: Date.now(),
      decided: null,
      resolver: resolve
    }
    tickets.set(id, ticket)
    addJarvisNotification({
      title: `Approval needed (${args.level})`,
      message: args.summary.slice(0, 160),
      type: 'warning'
    })
  })
}

export function decideApproval(id: string, approved: boolean): void {
  const ticket = tickets.get(id)
  if (!ticket || ticket.decided !== null) return
  ticket.decided = approved
  try { ticket.resolver?.(approved) } catch { /* noop */ }
  tickets.delete(id)
}

export function pendingApprovals(): ApprovalTicket[] {
  return Array.from(tickets.values())
}

export function cancelApprovalsFor(reason: string): void {
  for (const ticket of tickets.values()) {
    ticket.decided = false
    try { ticket.resolver?.(false) } catch { /* noop */ }
    void reason
  }
  tickets.clear()
}
