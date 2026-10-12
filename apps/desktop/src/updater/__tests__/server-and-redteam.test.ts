import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { describe, expect, it } from 'vitest';

import { createUpdateRequestHandler, UpdateServer } from '../../../../../services/update/update-server';
import { verifyManifest } from '../manifest-verifier';
import type { UpdateManifest } from '../types';

function testStorage(): string {
  return join(tmpdir(), `test-update-storage-${process.pid}-${Date.now()}-${Math.random().toString(36).slice(2)}`);
}

type Req = { method?: string; url?: string };

function makeRes() {
  const chunks: Array<string | Buffer> = [];
  let status = 0;
  let headers: Record<string, string> = {};

  return {
    get status() { return status; },
    get headers() { return headers; },
    get body() { return Buffer.concat(chunks.map((c) => (typeof c === 'string' ? Buffer.from(c) : c))).toString(); },
    res: {
      writeHead(s: number, h?: Record<string, string>) { status = s; headers = h ?? {}; },
      end(b?: string | Buffer) { if (b) {chunks.push(b);} },
    },
  };
}

async function publishedServer() {
  const server = new UpdateServer(testStorage());

  const manifest = await server.createRelease(
    '1.2.0', 'stable', new Map([['linux-x64', Buffer.from('artifact-bytes-payload')]]),
    'deadbeef',
    { builder: 'AetherOS', buildTimestamp: new Date().toISOString(), buildWorkflow: 'test', dependencies: [] },
    { classification: 'normal' }, 'notes',
  );

  await server.publishRelease(manifest.releaseId);
  // Deterministic serving: open rollout fully (default stable starts at 5%).
  await server.configureRollout('stable', { percentage: 100, startDate: new Date().toISOString() });
  const published = server.getRelease(manifest.releaseId)!;
  published.rollout.percentage = 100;

  return { server, manifest: published };
}

describe('update server endpoints', () => {
  it('serves latest manifest + artifact bytes + 404s unknown', async () => {
    const { server } = await publishedServer();
    const handle = createUpdateRequestHandler(server, { baseUrl: 'https://releases.aetheros.com', requireHttps: true });

    const r1 = makeRes();
    await handle({ method: 'GET', url: '/updates/linux/x64/stable' }, r1.res);
    expect(r1.status).toBe(200);
    const manifest = JSON.parse(r1.body) as UpdateManifest;
    expect(manifest.version).toBe('1.2.0');

    const r2 = makeRes();
    await handle({ method: 'GET', url: `/artifacts/stable/1.2.0/linux-x64` }, r2.res);
    expect(r2.status).toBe(200);
    expect(r2.headers['content-type']).toBe('application/octet-stream');

    const r3 = makeRes();
    await handle({ method: 'GET', url: '/updates/linux/x64/stable/9.9.9' }, r3.res);
    expect(r3.status).toBe(404);
  });

  it('rejects non-https base URLs in production', () => {
    const server = new UpdateServer('./x');
    expect(() => createUpdateRequestHandler(server, { baseUrl: 'http://evil.example.com' })).toThrow('https');
  });

  it('kill-switches and exposes previous-known-good', async () => {
    const { server, manifest } = await publishedServer();
    await server.revokeRelease(manifest.releaseId, 'broken');
    const handle = createUpdateRequestHandler(server, { baseUrl: 'https://releases.aetheros.com' });
    const r = makeRes();
    await handle({ method: 'GET', url: '/updates/linux/x64/stable' }, r.res);
    // Revoked release must not be served as current.
    expect(r.status).toBe(404);
    const rel = makeRes();
    await handle({ method: 'GET', url: `/updates/releases/${manifest.releaseId}` }, rel.res);
    expect(rel.status).toBe(200);
  });
});

describe('manifest red-team (§72)', () => {
  async function baseManifest(): Promise<{ manifest: UpdateManifest; publicKey: string }> {
    const server = new UpdateServer(testStorage());

    const manifest = await server.createRelease(
      '1.2.0', 'stable', new Map([['linux-x64', Buffer.from('artifact-bytes-payload')]]),
      'deadbeef',
      { builder: 'AetherOS', buildTimestamp: new Date().toISOString(), buildWorkflow: 'test', dependencies: [] },
      { classification: 'normal' }, 'notes',
    );

    return { manifest: JSON.parse(JSON.stringify(manifest)) as UpdateManifest, publicKey: server.getPublicKey() };
  }

  const opts = (m: UpdateManifest, extra = {}) => ({
    currentVersion: '1.1.0', channel: 'stable' as const, platform: 'linux' as const,
    architecture: 'x64' as const, ...extra,
  });

  it('accepts the genuine manifest (real RSA signature)', async () => {
    const { manifest, publicKey } = await baseManifest();
    const r = await verifyManifest(manifest, opts(manifest, { publicKey }));
    expect(r.valid).toBe(true);
  });

  it('rejects downgrade/replay of an older version', async () => {
    const { manifest } = await baseManifest();
    const r = await verifyManifest(manifest, opts(manifest, { currentVersion: '1.2.0' }));
    expect(r.valid).toBe(false);
    expect(r.errors.some((e) => e.code === 'DOWNGRADE_FORBIDDEN')).toBe(true);
  });

  it('rejects wrong-platform artifacts', async () => {
    const { manifest } = await baseManifest();
    const r = await verifyManifest(manifest, opts(manifest, { platform: 'darwin' as never, architecture: 'arm64' as never }));
    expect(r.errors.some((e) => e.code === 'UNSUPPORTED_PLATFORM')).toBe(true);
  });

  it('rejects http (MITM) artifact URLs', async () => {
    const { manifest } = await baseManifest();
    manifest.artifacts[0].url = 'http://evil.example.com/a.bin';
    manifest.platforms['linux-x64'].url = 'http://evil.example.com/a.bin';
    const r = await verifyManifest(manifest, opts(manifest));
    expect(r.errors.length).toBeGreaterThan(0);
  });

  it('rejects tampered hashes (real signature no longer matches)', async () => {
    const { manifest, publicKey } = await baseManifest();
    manifest.artifacts[0].sha256 = '0'.repeat(64);
    manifest.platforms['linux-x64'].sha256 = '0'.repeat(64);
    const r1 = await verifyManifest(manifest, opts(manifest, { publicKey }));
    expect(r1.errors.some((e) => e.code === 'SIGNATURE_INVALID')).toBe(true);
    manifest.artifacts[0].signature = '';
    manifest.platforms['linux-x64'].signature = '';
    const r2 = await verifyManifest(manifest, opts(manifest));
    expect(r2.errors.some((e) => e.code === 'SIGNATURE_INVALID')).toBe(true);
  });

  it('refuses revoked releases', async () => {
    const { manifest } = await baseManifest();
    manifest.rollout.killSwitch = true;
    const r = await verifyManifest(manifest, opts(manifest));
    expect(r.errors.some((e) => e.code === 'REVOKED_RELEASE')).toBe(true);
  });
});
