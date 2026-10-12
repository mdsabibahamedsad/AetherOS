import { describe, expect, it } from 'vitest';

import {
  currentBackoffMs, DEFAULT_CHECK_POLICY, isRolloutEligible,
  jitteredBackoffMs, recordCheckFailure,
  recordCheckSuccess, rolloutBucket, shouldCheckNow, withTimeout,
} from '../update-policy';

describe('check policy', () => {
  it('checks on first run and after interval', () => {
    expect(shouldCheckNow(0, DEFAULT_CHECK_POLICY)).toBe(true);
    const now = Date.now();
    expect(shouldCheckNow(now - 1000, DEFAULT_CHECK_POLICY, now)).toBe(false);
    expect(shouldCheckNow(now - DEFAULT_CHECK_POLICY.checkIntervalMs - 1, DEFAULT_CHECK_POLICY, now)).toBe(true);
  });

  it('backs off exponentially with cap', () => {
    let p = DEFAULT_CHECK_POLICY;
    expect(currentBackoffMs(p)).toBe(0);
    p = recordCheckFailure(p);
    expect(currentBackoffMs(p)).toBe(60_000);
    p = recordCheckFailure(p);
    expect(currentBackoffMs(p)).toBe(120_000);
    p = { ...p, consecutiveFailures: 100 };
    expect(currentBackoffMs(p)).toBe(p.backoffMaxMs);
    p = recordCheckSuccess(p);
    expect(currentBackoffMs(p)).toBe(0);
  });

  it('jitter stays within [0, backoff]', () => {
    const p = recordCheckFailure(DEFAULT_CHECK_POLICY);

    for (let i = 0; i < 50; i++) {
      const j = jitteredBackoffMs(p);
      expect(j).toBeGreaterThanOrEqual(0);
      expect(j).toBeLessThanOrEqual(60_000);
    }
  });

  it('times out slow checks', async () => {
    await expect(withTimeout(new Promise(() => {}), 20, 'test')).rejects.toThrow('timed out');
    await expect(withTimeout(Promise.resolve(42), 1000)).resolves.toBe(42);
  });
});

describe('rollout gating', () => {
  it('is stable per device and honors kill switch', () => {
    const gate = { percentage: 50, releaseId: 'r1' };
    const a = rolloutBucket('r1', 'device-1');
    expect(rolloutBucket('r1', 'device-1')).toBe(a); // stable
    expect(isRolloutEligible({ ...gate, killSwitch: true }, 'device-1')).toBe(false);
    expect(isRolloutEligible({ percentage: 100, releaseId: 'r1' }, 'any')).toBe(true);
    expect(isRolloutEligible({ percentage: 0, releaseId: 'r1' }, 'any')).toBe(false);
  });

  it('splits cohorts roughly by percentage', () => {
    const gate = { percentage: 10, releaseId: 'r2' };
    let eligible = 0;

    for (let i = 0; i < 1000; i++) {
      if (isRolloutEligible(gate, `device-${i}`)) {eligible++;}
    }

    expect(eligible).toBeGreaterThan(30);
    expect(eligible).toBeLessThan(200);
  });
});
