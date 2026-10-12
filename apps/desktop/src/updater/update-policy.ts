/**
 * Update Policy — check scheduling, backoff/jitter, rollout eligibility.
 *
 * Spec (§12, §30–§32): configurable startup / periodic / manual /
 * background checks with exponential backoff + jitter + timeout +
 * offline handling. Rollout gating uses a stable device-hash bucket so a
 * device stays in/out of a staged rollout across checks without the
 * server tracking individual devices (no PII).
 */

import { createHash } from 'node:crypto';

export interface CheckPolicy {
  /** Minimum ms between automatic checks. */
  checkIntervalMs: number;
  /** Base backoff after a failed check. */
  backoffBaseMs: number;
  /** Maximum backoff cap. */
  backoffMaxMs: number;
  /** Request timeout. */
  timeoutMs: number;
  /** Consecutive failures tracked for backoff. */
  consecutiveFailures: number;
}

export const DEFAULT_CHECK_POLICY: CheckPolicy = {
  checkIntervalMs: 24 * 60 * 60 * 1000,
  backoffBaseMs: 60 * 1000,
  backoffMaxMs: 6 * 60 * 60 * 1000,
  timeoutMs: 30 * 1000,
  consecutiveFailures: 0,
};

export function shouldCheckNow(lastCheckAt: number, policy: CheckPolicy, now = Date.now()): boolean {
  if (lastCheckAt <= 0) {return true;}
  const backoff = currentBackoffMs(policy);
  const wait = Math.max(policy.checkIntervalMs, backoff);

  return now - lastCheckAt >= wait;
}

/** Exponential backoff: base * 2^failures, capped. Zero failures → 0. */
export function currentBackoffMs(policy: CheckPolicy): number {
  if (policy.consecutiveFailures <= 0) {return 0;}
  const backoff = policy.backoffBaseMs * 2 ** (policy.consecutiveFailures - 1);

  return Math.min(backoff, policy.backoffMaxMs);
}

/** Full jitter: uniform random in [0, backoff]. Inject rand for tests. */
export function jitteredBackoffMs(policy: CheckPolicy, rand: () => number = Math.random): number {
  const backoff = currentBackoffMs(policy);

  if (backoff <= 0) {return 0;}

  return Math.floor(rand() * backoff);
}

export function recordCheckSuccess(policy: CheckPolicy): CheckPolicy {
  return { ...policy, consecutiveFailures: 0 };
}

export function recordCheckFailure(policy: CheckPolicy): CheckPolicy {
  return { ...policy, consecutiveFailures: policy.consecutiveFailures + 1 };
}

export interface RolloutGate {
  percentage: number;
  killSwitch?: boolean;
  releaseId: string;
}

/**
 * Stable rollout bucket: sha256(releaseId + ':' + deviceId) mod 100.
 * Device IDs are local opaque install IDs — never transmitted.
 */
export function rolloutBucket(releaseId: string, deviceId: string): number {
  const hex = createHash('sha256').update(`${releaseId}:${deviceId}`).digest('hex');

  return parseInt(hex.slice(0, 8), 16) % 100;
}

export function isRolloutEligible(gate: RolloutGate, deviceId: string): boolean {
  if (gate.killSwitch) {return false;}

  if (gate.percentage >= 100) {return true;}

  if (gate.percentage <= 0) {return false;}

  return rolloutBucket(gate.releaseId, deviceId) < gate.percentage;
}

/** Wrap a promise with a timeout (spec §12: timeout + offline handling). */
export function withTimeout<T>(promise: Promise<T>, timeoutMs: number, label = 'update-check'): Promise<T> {
  let timer: ReturnType<typeof setTimeout> | undefined;

  const timeout = new Promise<never>((_, reject) => {
    timer = setTimeout(() => reject(new Error(`${label} timed out after ${timeoutMs}ms`)), timeoutMs);
  });

  return Promise.race([promise, timeout]).finally(() => {
    if (timer) {clearTimeout(timer);}
  });
}
