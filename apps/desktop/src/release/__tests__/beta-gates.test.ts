import { generateKeyPairSync } from 'node:crypto';

import { describe, expect, it } from 'vitest';

import { buildSupportBundle, redactSecrets, signFlags, verifyFlags } from '../beta-flags';
import {
  CHANNEL_POLICIES,
  comparePerf,
  DEFAULT_THRESHOLDS,
  evaluateBetaExit,
  evaluateRolloutGate,
} from '../beta-gates';

describe('channel policy', () => {
  it('beta requires signing+SBOM+provenance+rollback, starts at <=10%', () => {
    const beta = CHANNEL_POLICIES.beta;
    expect(beta.signedArtifactsRequired).toBe(true);
    expect(beta.sbomRequired).toBe(true);
    expect(beta.provenanceRequired).toBe(true);
    expect(beta.rollbackRequired).toBe(true);
    expect(beta.maxRolloutStartPct).toBeLessThanOrEqual(10);
    expect(beta.autoPromote).toBe(false);
  });
});

describe('rollout gates', () => {
  const healthy = {
    crashRatePct: 0.2, startupFailurePct: 0.1, updateFailurePct: 1,
    authFailurePct: 0, securityAlerts: 0, userReportedCritical: 0,
  };

  it('passes healthy telemetry', () => {
    const d = evaluateRolloutGate(healthy, DEFAULT_THRESHOLDS);
    expect(d.status).toBe('PASS');
  });

  it('holds on breached threshold', () => {
    const d = evaluateRolloutGate({ ...healthy, crashRatePct: 5 }, DEFAULT_THRESHOLDS);
    expect(d.status).toBe('HOLD');
  });

  it('rolls back on security alert or critical user report', () => {
    expect(evaluateRolloutGate({ ...healthy, securityAlerts: 1 }).status).toBe('ROLLBACK');
    expect(evaluateRolloutGate({ ...healthy, userReportedCritical: 2 }).status).toBe('ROLLBACK');
  });

  it('marks missing telemetry UNVERIFIED, never passes', () => {
    const d = evaluateRolloutGate({
      crashRatePct: null, startupFailurePct: null, updateFailurePct: null,
      authFailurePct: null, securityAlerts: null, userReportedCritical: null,
    });

    expect(d.status).toBe('UNVERIFIED');
    expect(d.status).not.toBe('PASS');
  });
});

describe('beta exit', () => {
  it('is NOT_READY with any FAIL or UNVERIFIED', () => {
    const cats = ['p0', 'security', 'artifacts', 'update', 'rollback', 'platforms', 'knownIssues', 'support', 'monitoring', 'incidentResponse'] as const;
    const full = cats.map((category) => ({ category, met: true as const, evidence: 'e' }));
    expect(evaluateBetaExit(full).overall).toBe('READY');
    const missing = full.slice(0, 9).map((c) => ({ ...c, met: c.met as boolean | null }));
    expect(evaluateBetaExit(missing).overall).toBe('NOT_READY');
    const failed = full.map((c) => (c.category === 'security' ? { ...c, met: false as const } : c));
    const score = evaluateBetaExit(failed);
    expect(score.overall).toBe('NOT_READY');
    expect(score.blockers.join(' ')).toMatch(/security/);
  });
});

describe('perf comparison', () => {
  it('flags regressions above threshold, unverified on nulls', () => {
    const { regressions, unverified } = comparePerf(
      { startupMs: 1000, memoryMB: 200, agentLatencyMs: null },
      { startupMs: 1300, memoryMB: 205, agentLatencyMs: null },
      10,
    );

    expect(regressions.find((r) => r.metric === 'startupMs')?.regressed).toBe(true);
    expect(regressions.find((r) => r.metric === 'memoryMB')?.regressed).toBe(false);
    expect(unverified).toEqual(['agentLatencyMs']);
  });
});

describe('signed flags + support bundle', () => {
  const { publicKey, privateKey } = generateKeyPairSync('rsa', {
    modulusLength: 2048,
    publicKeyEncoding: { type: 'spki', format: 'pem' },
    privateKeyEncoding: { type: 'pkcs8', format: 'pem' },
  });

  it('accepts valid envelope, rejects tampered/expired/locked', () => {
    const env = signFlags({ newUI: true }, 'beta', 60_000, 'n1', privateKey);
    expect(verifyFlags(env, publicKey, 'beta').accepted).toBe(true);
    expect(verifyFlags({ ...env, flags: { newUI: false } }, publicKey, 'beta').accepted).toBe(false);
    expect(verifyFlags(env, publicKey, 'stable').accepted).toBe(false);
    const expired = signFlags({ a: 1 }, 'beta', -1, 'n2', privateKey);
    expect(verifyFlags(expired, publicKey, 'beta').accepted).toBe(false);
    const locked = signFlags({ disableSandbox: true }, 'beta', 60_000, 'n3', privateKey);
    const d = verifyFlags(locked, publicKey, 'beta');
    expect(d.accepted).toBe(false);
    expect(d.reason).toMatch(/SECURITY_LOCKED/);
  });

  it('redacts secrets from logs and diagnostics', () => {
    expect(redactSecrets('Authorization: Bearer abcdefgh123456')).toMatch(/\[REDACTED\]/);

    const bundle = buildSupportBundle({
      version: '1.1.0-beta.1', platform: 'win32', architecture: 'x64',
      releaseId: 'r', channel: 'beta', logs: 'token=supersecret-value here',
      health: {}, updateState: 'IDLE',
      diagnostics: { apiKey: 'zzz', nested: { password: 'p' }, ok: 'fine' },
    });

    const s = JSON.stringify(bundle);
    expect(s).not.toMatch(/supersecret-value/);
    expect(s).not.toMatch(/zzz/);
    expect(s).toMatch(/fine/);
  });
});
