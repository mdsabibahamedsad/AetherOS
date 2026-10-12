/**
 * Signed feature flags (Master 74 §45) + redacted support bundle (§43).
 *
 * Flags are server-issued, RSA-signed envelopes: clients verify before
 * applying. Flags can NEVER weaken security controls — SECURITY_LOCKED
 * flags are rejected even when signed (defense in depth).
 */

import { createSign, createVerify } from 'node:crypto';

export interface FlagEnvelope {
  flags: Record<string, string | boolean | number>;
  scope: string;
  issuedAt: string;
  expiresAt: string;
  nonce: string;
  signature: string;
}

/** Flags that must never be flipped by remote config, signed or not. */
const SECURITY_LOCKED = new Set([
  'disableSignatureVerification',
  'disableAuthentication',
  'disableSandbox',
  'disableAuditLog',
  'elevateAutonomy',
]);

export function stableStringify(value: unknown): string {
  if (value === null || typeof value !== 'object') {
    return JSON.stringify(value);
  }

  if (Array.isArray(value)) {
    return `[${(value as unknown[]).map(stableStringify).join(',')}]`;
  }

  return `{${Object.entries(value as Record<string, unknown>)
    .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
    .map(([k, v]) => `${JSON.stringify(k)}:${stableStringify(v)}`)
    .join(',')}}`;
}

function canonicalEnvelope(env: FlagEnvelope): string {
  const { signature: _s, ...rest } = env;

  return stableStringify(rest);
}

export function signFlags(
  flags: FlagEnvelope['flags'], scope: string, ttlMs: number, nonce: string,
  privateKey: string, now = Date.now(),
): FlagEnvelope {
  const env: FlagEnvelope = {
    flags, scope,
    issuedAt: new Date(now).toISOString(),
    expiresAt: new Date(now + ttlMs).toISOString(),
    nonce, signature: '',
  };

  env.signature = createSign('sha256').update(canonicalEnvelope(env)).end().sign(privateKey, 'base64');

  return env;
}

export interface FlagDecision {
  accepted: boolean;
  flags: Record<string, string | boolean | number>;
  reason: string;
}

export function verifyFlags(env: FlagEnvelope, publicKey: string, expectedScope: string, now = Date.now()): FlagDecision {
  const reject = (reason: string): FlagDecision => ({ accepted: false, flags: {}, reason });

  if (!env.signature) {
    return reject('missing signature');
  }

  let ok = false;

  try {
    ok = createVerify('sha256').update(canonicalEnvelope(env)).end()
      .verify(publicKey, Buffer.from(env.signature, 'base64'));
  } catch {
    return reject('signature verify error');
  }

  if (!ok) {
    return reject('SIGNATURE_INVALID');
  }

  if (env.scope !== expectedScope) {
    return reject(`scope mismatch: ${env.scope} != ${expectedScope}`);
  }

  if (Date.parse(env.expiresAt) <= now) {
    return reject('envelope expired');
  }

  const locked = Object.keys(env.flags).filter((k) => SECURITY_LOCKED.has(k));

  if (locked.length > 0) {
    return reject(`SECURITY_LOCKED flags rejected: ${locked.join(',')}`);
  }

  return { accepted: true, flags: { ...env.flags }, reason: 'verified' };
}

// --- Support bundle (§43) ------------------------------------------------------

const SECRET_KEYS = [/token/i, /secret/i, /password/i, /api[_-]?key/i, /private[_-]?key/i, /auth/i, /cookie/i];

export interface SupportBundleInput {
  version: string;
  platform: string;
  architecture: string;
  releaseId: string;
  channel: string;
  logs: string;
  health: unknown;
  updateState: unknown;
  diagnostics: Record<string, unknown>;
}

export function redactSecrets(text: string): string {
  let out = text;
  // Redact bearer/basic credentials and key=value secrets.
  out = out.replace(/(bearer\s+)[A-Za-z0-9\-._~+/=]{8,}/gi, '$1[REDACTED]');
  out = out.replace(/(["']?(?:token|secret|password|api[_-]?key|private[_-]?key)["']?\s*[:=]\s*["']?)([^"'\s,}]+)/gi, '$1[REDACTED]');

  return out;
}

export function redactObject(obj: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {};

  for (const [k, v] of Object.entries(obj)) {
    if (SECRET_KEYS.some((re) => re.test(k))) {
      out[k] = '[REDACTED]';
    } else if (typeof v === 'string') {
      out[k] = redactSecrets(v);
    } else if (v !== null && typeof v === 'object' && !Array.isArray(v)) {
      out[k] = redactObject(v as Record<string, unknown>);
    } else {
      out[k] = v;
    }
  }

  return out;
}

export function buildSupportBundle(input: SupportBundleInput): Record<string, unknown> {
  return {
    product: 'AetherOS',
    version: input.version,
    platform: input.platform,
    architecture: input.architecture,
    releaseId: input.releaseId,
    channel: input.channel,
    collectedAt: new Date().toISOString(),
    logs: redactSecrets(input.logs).slice(0, 200_000),
    health: input.health,
    updateState: input.updateState,
    diagnostics: redactObject(input.diagnostics),
  };
}
