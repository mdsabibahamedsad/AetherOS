/**
 * Jarvis tool permission policy.
 *
 * Every capability declares required permissions (see the capability
 * registry). This module decides, per permission class, whether an action
 * may proceed, must ask first, or is denied. Pure logic — the persisted
 * policy lives in `store/jarvis-permissions.ts`.
 *
 * Hard invariants (cannot be configured away):
 * - `destructive` and `communicate` ALWAYS require explicit approval.
 * - Voice input NEVER bypasses approval.
 * - A deny always wins over an allow.
 */

import type { Capability, CapabilityPermission } from '../capabilities/registry'

export type PolicyDecision = 'allow' | 'ask' | 'deny'

export type PermissionRule = 'ask' | 'allow-session' | 'always-allow' | 'deny'

export type PermissionPolicy = Record<CapabilityPermission, PermissionRule>

export const DEFAULT_POLICY: PermissionPolicy = {
  read: 'always-allow',
  write: 'ask',
  execute: 'ask',
  network: 'ask',
  communicate: 'ask',
  system: 'ask',
  destructive: 'ask'
}

/** Permissions that can never be set to always-allow. */
const ALWAYS_ASK: ReadonlySet<CapabilityPermission> = new Set(['destructive', 'communicate'])

export function sanitizePolicy(policy: Partial<PermissionPolicy>): PermissionPolicy {
  const next: PermissionPolicy = { ...DEFAULT_POLICY, ...policy }

  for (const perm of ALWAYS_ASK) {
    if (next[perm] === 'always-allow') {next[perm] = 'ask'}
  }

  return next
}

export interface ApprovalContext {
  policy: PermissionPolicy
  /** Permissions the user already approved for this session. */
  sessionGrants: Set<CapabilityPermission>
  /** Input channel. Voice never bypasses approval (same rule, explicit). */
  inputType: 'text' | 'voice'
}

/**
 * Decide whether a capability may run. Returns the decision plus the
 * permission that determined it, so the UI can explain itself.
 */
export function decideCapability(
  capability: Capability,
  ctx: ApprovalContext
): { decision: PolicyDecision; permission: CapabilityPermission | null } {
  if (capability.permissions.length === 0) {return { decision: 'allow', permission: null }}

  let worst: PolicyDecision = 'allow'
  let worstPerm: CapabilityPermission | null = null

  for (const perm of capability.permissions) {
    const rule = ctx.policy[perm] ?? 'ask'
    let decision: PolicyDecision

    if (rule === 'deny') {decision = 'deny'}
    else if (rule === 'always-allow' && !ALWAYS_ASK.has(perm)) {decision = 'allow'}
    else if ((rule === 'allow-session' || rule === 'always-allow') && ctx.sessionGrants.has(perm)) {decision = 'allow'}
    else {decision = 'ask'}

    // Voice follows the identical rule — stated here so no future edit can
    // quietly exempt it. (No branch needed: same decision either way.)
    void ctx.inputType

    if (decision === 'deny') {return { decision: 'deny', permission: perm }}

    if (decision === 'ask') {
      worst = 'ask'
      worstPerm = perm
    }
  }

  return { decision: worst, permission: worstPerm }
}

/** Local destructive patterns that always need approval, even before routing. */
const DESTRUCTIVE_PATTERNS: RegExp[] = [
  /\b(delete|remove|erase|wipe|format|destroy)\b/i,
  /\b(drop\s+table|truncate)\b/i,
  /\brm\s+-rf?\b/,
  /\bkill\s+-9\b/,
  /\bsend\b.*\b(email|message|dm)\b/i,
  /\bpublish\b/i,
  /\btransfer\b.*\b(money|funds|payment)\b/i
]

export function looksDestructive(input: string): boolean {
  return DESTRUCTIVE_PATTERNS.some(re => re.test(input))
}
