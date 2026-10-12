/**
 * Deterministic Jarvis tool router.
 *
 * The model may suggest tools, but the runtime validates every call:
 * tool exists → input schema valid → permission valid → resource
 * accessible. Invalid calls return structured errors, never execute.
 */

import {
  CAPABILITIES,
  getCapability,
  type Capability
} from '../capabilities/registry'
import { decideCapability, type PermissionPolicy } from '../permissions/policy'
import type { CapabilityPermission } from '../capabilities/registry'

export interface RouteResult {
  capability: Capability
  input: Record<string, string>
}

export interface RouteError {
  code: 'NO_MATCH' | 'UNKNOWN_TOOL' | 'INVALID_ARGS' | 'DENIED' | 'UNAVAILABLE'
  message: string
}

interface LocalPattern {
  capabilityId: string
  pattern: RegExp
  build: (m: RegExpMatchArray, raw: string) => Record<string, string>
}

const APP_IDS = ['chrome', 'youtube', 'vscode', 'spotify'] as const

const LOCAL_PATTERNS: LocalPattern[] = [
  {
    capabilityId: 'computer.launch-app',
    pattern: /^open\s+([a-z0-9 .+]+)\.?$/i,
    build: m => {
      const id = m[1].trim().toLowerCase().replace(/[. ]+$/, '')
      const normalized = id === 'vs code' ? 'vscode' : id
      return { appId: normalized }
    }
  },
  {
    capabilityId: 'computer.open-url',
    pattern: /^open\s+(https?:\/\/\S+)\.?$/i,
    build: m => ({ url: m[1] })
  },
  {
    capabilityId: 'system.navigate',
    pattern: /^(exit(\s+(jarvis|jarvis\s+mode))?|leave\s+jarvis|quit\s+jarvis|go\s+back|return\s+home|go\s+home)$/i,
    build: () => ({ route: '/' })
  },
  {
    capabilityId: 'system.navigate',
    pattern: /^(open|go\s+to|show\s+me)\s+(memory|agents|automation|browser|terminal|settings|security(\s+center)?|diagnostics|home|chat|knowledge|communications)(\s+(center|panel|page|view))?$/i,
    build: m => {
      const dest = m[2].replace(/\s+center$/, '')
      return { route: dest === 'home' ? '/' : dest === 'security' ? '/security' : `/${dest}` }
    }
  },
  {
    capabilityId: 'system.status',
    pattern: /^(check\s+)?(system\s+)?(health|status)$|^system\s+status$/i,
    build: () => ({})
  },
  {
    capabilityId: 'models.inspect',
    pattern: /^(what\s+model|which\s+model|show\s+(available\s+)?models)$/i,
    build: () => ({})
  }
]

const GATEWAY_HINTS: Array<{ match: RegExp; capabilityId: string; build: (raw: string) => Record<string, string> }> = [
  { match: /\bsearch the web\b|\bgoogle\b/i, capabilityId: 'browser.search-web', build: raw => ({ query: raw }) },
  { match: /\brun\b.*\b(npm|pytest|test|build|lint|tsc)\b/i, capabilityId: 'code.test', build: raw => ({ scope: raw.slice(0, 200) }) },
  { match: /\bfind\b.*\b(pdf|file|report|doc)\b/i, capabilityId: 'files.search', build: raw => ({ query: raw }) },
  { match: /\bremember\b/i, capabilityId: 'memory.remember', build: raw => ({ fact: raw }) },
  { match: /\bschedule\b|\bremind\b|\bevery (morning|monday|day|week)\b/i, capabilityId: 'automation.schedule', build: raw => ({ instruction: raw }) },
  { match: /\bnavigate\b|\bbrowse to\b|\bopen browser\b/i, capabilityId: 'browser.navigate', build: raw => ({ url: raw }) }
]

export function routeCommand(raw: string): RouteResult | RouteError {
  const input = raw.trim().replace(/\s+/g, ' ')
  if (!input) return { code: 'INVALID_ARGS', message: 'Empty command.' }

  for (const p of LOCAL_PATTERNS) {
    const m = input.match(p.pattern)
    if (!m) continue
    const cap = getCapability(p.capabilityId)
    if (!cap) return { code: 'UNKNOWN_TOOL', message: `Unknown capability "${p.capabilityId}".` }
    if (cap.id === 'computer.launch-app') {
      const appId = (p.build(m, input).appId ?? '').toLowerCase()
      if (!(APP_IDS as readonly string[]).includes(appId)) continue // not allowlisted → gateway path
    }
    return { capability: cap, input: p.build(m, input) }
  }

  for (const h of GATEWAY_HINTS) {
    if (h.match.test(input)) {
      const cap = getCapability(h.capabilityId)
      if (!cap) return { code: 'UNKNOWN_TOOL', message: `Unknown capability "${h.capabilityId}".` }
      return { capability: cap, input: h.build(input) }
    }
  }

  return { code: 'NO_MATCH', message: 'No deterministic route — send to the gateway agent.' }
}

export interface ValidationCtx {
  policy: PermissionPolicy
  sessionGrants: Set<CapabilityPermission>
  gatewayOpen: boolean
  localHandlers: Set<string>
  inputType: 'text' | 'voice'
}

/** Full validation gate: existence → schema → permission → availability. */
export function validateToolCall(
  capabilityId: string,
  input: Record<string, string>,
  ctx: ValidationCtx
): { ok: true; capability: Capability } | RouteError {
  const cap = getCapability(capabilityId)
  if (!cap) return { code: 'UNKNOWN_TOOL', message: `Tool "${capabilityId}" does not exist.` }

  const missing = cap.inputSchema.required.filter(k => !input[k]?.trim())
  if (missing.length > 0) {
    return { code: 'INVALID_ARGS', message: `Missing required argument(s): ${missing.join(', ')}.` }
  }

  const { decision, permission } = decideCapability(cap, {
    policy: ctx.policy,
    sessionGrants: ctx.sessionGrants,
    inputType: ctx.inputType
  })
  if (decision === 'deny') {
    return { code: 'DENIED', message: `Blocked by permission policy (${permission}).` }
  }

  if (cap.binding.via === 'gateway-agent') {
    if (!ctx.gatewayOpen) return { code: 'UNAVAILABLE', message: 'Gateway disconnected — reconnect to enable agent capabilities.' }
  } else {
    if (!ctx.localHandlers.has(cap.binding.handler)) {
      return { code: 'UNAVAILABLE', message: `Local handler "${cap.binding.handler}" is not registered.` }
    }
  }

  return { ok: true, capability: cap }
}

export function listCapabilityIds(): string[] {
  return CAPABILITIES.map(c => c.id)
}
