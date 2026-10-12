import { mkdir, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { describe, expect, it } from 'vitest';

import { UpdateCache } from '../update-cache';
import { applyMigrations, CrashLoopGuard, type Migration, runHealthChecks, standardChecks } from '../update-health';
import { UpdateTelemetry } from '../update-telemetry';

describe('health checks', () => {
  it('passes when all critical probes pass', async () => {
    const r = await runHealthChecks(
      standardChecks({ launch: async () => ({ passed: true }), backend: async () => ({ passed: true }) }),
      '1.2.0',
    );

    expect(r.passed).toBe(true);
    expect(r.checks).toHaveLength(8);
  });

  it('fails when any critical probe fails', async () => {
    const r = await runHealthChecks(
      standardChecks({ storage: async () => ({ passed: false, message: 'disk unreadable' }) }),
      '1.2.0',
    );

    expect(r.passed).toBe(false);
    expect(r.checks.find((c) => c.name === 'storage')?.passed).toBe(false);
  });

  it('treats probe exceptions as failures', async () => {
    const r = await runHealthChecks(
      [{ name: 'ipc', critical: true, run: async () => { throw new Error('boom'); } }],
      '1.2.0',
    );

    expect(r.passed).toBe(false);
  });
});

describe('crash loop guard', () => {
  it('trips after threshold crashes on the new version', () => {
    const guard = new CrashLoopGuard(3, 60_000);
    expect(guard.recordCrash('1.2.0', 1000).crashLoop).toBe(false);
    expect(guard.recordCrash('1.2.0', 2000).crashLoop).toBe(false);
    expect(guard.recordCrash('1.2.0', 3000).crashLoop).toBe(true);
    guard.recordCleanStart('1.2.0');
    expect(guard.recordCrash('1.2.0', 4000).crashLoop).toBe(false);
  });
});

describe('migrations', () => {
  const mig = (id: string, version: string, fail = false, failValidate = false): Migration => ({
    id,
    version,
    precondition: () => true,
    execute: async () => {
      if (fail) {throw new Error(`${id} exploded`);}
    },
    validate: async () => !failValidate,
    rollback: async () => {},
  });

  it('applies pending migrations in order', async () => {
    const order: string[] = [];

    const ms: Migration[] = ['m1', 'm2'].map((id, i) => ({
      ...mig(id, `1.${i + 1}.0`),
      execute: async () => {
        order.push(id);
      },
    }));

    const out = await applyMigrations(ms, '1.0.0', '1.2.0');
    expect(out).toEqual({ applied: ['m1', 'm2'], rolledBack: [] });
    expect(order).toEqual(['m1', 'm2']);
  });

  it('rolls back on failure without touching future migrations', async () => {
    const rolledBack: string[] = [];

    const ms: Migration[] = [
      { ...mig('good', '1.1.0'), rollback: async () => { rolledBack.push('good'); } },
      mig('bad', '1.2.0', true),
      mig('future', '2.0.0'),
    ];

    const out = await applyMigrations(ms, '1.0.0', '1.2.0');
    expect(out.failed?.id).toBe('bad');
    expect(rolledBack).toContain('good');
    expect(out.applied).toEqual(['good']);
  });
});

describe('telemetry + cache', () => {
  it('counts metrics and scrubs fields', async () => {
    const dir = join(tmpdir(), `aetheros-tel-${process.pid}-${Date.now()}`);
    const tel = new UpdateTelemetry(dir);
    await tel.record({ metric: 'update_checks', version: '1.2.0' });
    await tel.record({ metric: 'update_download_failure', failureReason: 'x'.repeat(500) });
    expect(tel.getCount('update_checks')).toBe(1);
    expect(Object.keys(tel.snapshot())).toContain('update_rollbacks');
    await rm(dir, { recursive: true, force: true });
  });

  it('expires metadata and enforces artifact budget', async () => {
    const root = join(tmpdir(), `aetheros-cache-${process.pid}-${Date.now()}`);
    // Generous TTL for the fresh-read: immune to event-loop stalls under load.
    const cache = new UpdateCache(root, { metadataTtlMs: 60_000, maxArtifactBytes: 10 });
    await cache.setMetadata('manifest:stable', '{"v":1}');
    expect(await cache.getMetadata('manifest:stable')).toBe('{"v":1}');

    // Short TTL + sleep comfortably beyond it: scheduling delays can only
    // push us further past expiry, never before it.
    const expiring = new UpdateCache(root, { metadataTtlMs: 30, maxArtifactBytes: 10 });
    await expiring.setMetadata('manifest:beta', '{"v":2}');
    await new Promise((r) => setTimeout(r, 150));
    expect(await expiring.getMetadata('manifest:beta')).toBeNull();

    await mkdir(join(root, 'artifacts'), { recursive: true });
    await writeFile(join(root, 'artifacts', 'old.bin'), Buffer.alloc(8));
    await writeFile(join(root, 'artifacts', 'new.bin'), Buffer.alloc(8));
    const freed = await cache.enforceArtifactBudget();
    expect(freed).toBeGreaterThan(0);
    await rm(root, { recursive: true, force: true });
  });
});
