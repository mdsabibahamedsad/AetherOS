import { createHash, generateKeyPairSync, sign } from 'node:crypto';
import { mkdir, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { describe, expect, it } from 'vitest';

import type { ArtifactInfo, UpdateManifest } from '../types';
import {
  isHttpsUrl, sha256Buffer, stableStringify, verifyArtifactFile, verifyManifestSignature,
} from '../update-verifier';

const { publicKey, privateKey } = generateKeyPairSync('rsa', {
  modulusLength: 2048,
  publicKeyEncoding: { type: 'spki', format: 'pem' },
  privateKeyEncoding: { type: 'pkcs8', format: 'pem' },
});

const dir = join(tmpdir(), `aetheros-verify-test-${process.pid}`);

async function makeArtifact(bytes: Buffer, mutate?: (a: ArtifactInfo) => void): Promise<{ artifact: ArtifactInfo; path: string }> {
  await mkdir(dir, { recursive: true });
  const path = join(dir, `art-${Math.random().toString(36).slice(2)}.bin`);
  await writeFile(path, bytes);

  const artifact: ArtifactInfo = {
    platform: 'linux',
    architecture: 'x64',
    version: '1.2.0',
    buildId: 'b1',
    sourceCommit: 'c1',
    sha256: createHash('sha256').update(bytes).digest('hex'),
    size: bytes.length,
    signature: sign('sha256', bytes, privateKey).toString('base64'),
    url: 'https://releases.aetheros.com/desktop/1.2.0/AetherOS-1.2.0-linux-x64.AppImage',
    provenance: { builder: 'AetherOS', buildTimestamp: new Date().toISOString(), buildWorkflow: 'test', dependencies: [] },
    packaging: 'appimage',
  };

  mutate?.(artifact);

  return { artifact, path };
}

describe('update verifier', () => {
  it('accepts a valid artifact', async () => {
    const { artifact, path } = await makeArtifact(Buffer.from('hello-aetheros'));
    const r = await verifyArtifactFile(artifact, path, publicKey);
    expect(r).toEqual({ valid: true, errors: [] });
    await rm(path, { force: true });
  });

  it('rejects tampered bytes (hash mismatch)', async () => {
    const { artifact, path } = await makeArtifact(Buffer.from('original'));
    await writeFile(path, Buffer.from('tampered!!'));
    const r = await verifyArtifactFile(artifact, path, publicKey);
    expect(r.valid).toBe(false);
    expect(r.errors.join(' ')).toMatch(/mismatch/i);
    await rm(path, { force: true });
  });

  it('rejects wrong signature', async () => {
    const { artifact, path } = await makeArtifact(Buffer.from('data'), (a) => {
      a.signature = Buffer.from('forged').toString('base64');
    });

    const r = await verifyArtifactFile(artifact, path, publicKey);
    expect(r.valid).toBe(false);
    await rm(path, { force: true });
  });

  it('rejects non-https URLs', async () => {
    const { artifact, path } = await makeArtifact(Buffer.from('data'), (a) => {
      a.url = 'http://evil.example.com/a.bin';
    });

    const r = await verifyArtifactFile(artifact, path, publicKey);
    expect(r.valid).toBe(false);
    expect(isHttpsUrl('https://x.example')).toBe(true);
    expect(isHttpsUrl('http://x.example')).toBe(false);
    await rm(path, { force: true });
  });

  it('verifies manifest signatures and rejects tampering', () => {
    const base = {
      product: 'AetherOS', version: '1.2.0', channel: 'stable', releaseId: 'r',
      commit: 'c', platforms: {}, minimumVersion: '1.0.0', artifacts: [],
      releaseNotes: '', security: { classification: 'normal' },
      rollout: { percentage: 100, startDate: new Date().toISOString() },
      protocolVersion: 1, timestamp: new Date().toISOString(), signature: '',
    } as UpdateManifest;

    const { signature: _s, ...rest } = base;
    const canonical = stableStringify(rest);
    base.signature = sign('sha256', Buffer.from(canonical), privateKey).toString('base64');
    expect(verifyManifestSignature(base, publicKey)).toBe(true);
    expect(verifyManifestSignature({ ...base, version: '9.9.9' }, publicKey)).toBe(false);
    expect(sha256Buffer(Buffer.from('abc')).length).toBe(64);
  });
});
