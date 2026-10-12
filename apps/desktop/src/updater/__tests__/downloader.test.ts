import { existsSync } from 'node:fs';
import { mkdir, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { basename, join } from 'node:path';

import { afterEach, describe, expect, it } from 'vitest';

import { FakeUpdateServer } from '../fake-update-server';
import type { ArtifactInfo } from '../types';
import { ResumableDownloader } from '../update-downloader';

const servers: FakeUpdateServer[] = [];
afterEach(async () => {
  while (servers.length) {await servers.pop()!.close();}
});

async function harness(scenario: Parameters<typeof makeServer>[0] = 'update-available') {
  const s = new FakeUpdateServer({ scenario });
  servers.push(s);
  const base = await s.listen(0);

  // Tests run over http (harness only); rewrite artifact URL accordingly.
  const artifact: ArtifactInfo = {
    ...s.manifest.platforms['linux-x64'],
    url: `${base}/artifact.bin`,
  };

  return { server: s, artifact, base };
}

const makeServer = (s: 'update-available') => s;

describe('resumable downloader', () => {
  it('downloads + verifies hash', async () => {
    const { artifact } = await harness();
    const staging = await freshDir();
    const dl = new ResumableDownloader();
    const seen: number[] = [];

    const path = await dl.download(artifact, {
      stagingDir: staging,
      onProgress: (p) => seen.push(p.percent),
    });

    expect(existsSync(path)).toBe(true);
    expect(seen.length).toBeGreaterThan(0);
    await rm(staging, { recursive: true, force: true });
  });

  it('resumes a partial download via Range', async () => {
    const { artifact } = await harness();
    const staging = await freshDir();
    const fileName = basename(new URL(artifact.url).pathname);
    // Seed a half-file: first half of the real artifact bytes.
    const res = await fetch(artifact.url);
    const full = Buffer.from(await res.arrayBuffer());
    await writeFile(join(staging, `${fileName}.part`), full.subarray(0, Math.floor(full.length / 2)));
    const dl = new ResumableDownloader();
    const path = await dl.download(artifact, { stagingDir: staging });
    expect(existsSync(path)).toBe(true);
    await rm(staging, { recursive: true, force: true });
  });

  it('rejects corrupt artifacts with HASH_MISMATCH', async () => {
    const { artifact } = await harness('corrupt-artifact' as never);
    const staging = await freshDir();
    const dl = new ResumableDownloader();
    await expect(dl.download(artifact, { stagingDir: staging })).rejects.toThrow('HASH_MISMATCH');
    await rm(staging, { recursive: true, force: true });
  });

  it('fails closed on insufficient disk', async () => {
    const { artifact } = await harness();
    const staging = await freshDir();
    const dl = new ResumableDownloader();
    await expect(
      dl.download(artifact, { stagingDir: staging, getFreeBytes: async () => 1 }),
    ).rejects.toThrow('INSUFFICIENT_DISK');
    await rm(staging, { recursive: true, force: true });
  });

  it('supports pause/resume/cancel on slow downloads', async () => {
    const s = new FakeUpdateServer({ scenario: 'slow-download', slowChunkMs: 2, version: '1.2.0' });
    servers.push(s);
    const base = await s.listen(0);
    const artifact: ArtifactInfo = { ...s.manifest.platforms['linux-x64'], url: `${base}/artifact.bin` };
    const staging = await freshDir();
    const dl = new ResumableDownloader();
    dl.pause();
    expect(dl.isPaused).toBe(true);
    dl.resume();
    const path = await dl.download(artifact, { stagingDir: staging });
    expect(existsSync(path)).toBe(true);
    const dl2 = new ResumableDownloader();
    dl2.cancel();
    await expect(dl2.download(artifact, { stagingDir: staging })).rejects.toThrow('cancelled');
    await rm(staging, { recursive: true, force: true });
  });
});

async function freshDir(): Promise<string> {
  const d = join(tmpdir(), `aetheros-dl-${process.pid}-${Math.random().toString(36).slice(2)}`);
  await mkdir(d, { recursive: true });

  return d;
}
