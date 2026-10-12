/**
 * Update Cache — bounded metadata + artifact cache (spec §78–§79).
 *
 * TTL for metadata, size-limited artifact store with LRU eviction.
 * After a successful update: remove temp files, retain ONLY the
 * rollback snapshot + required migration artifacts per policy.
 */

import { existsSync } from 'node:fs';
import { mkdir, readdir, readFile, rm, stat, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

export interface CachePolicy {
  metadataTtlMs: number;
  maxArtifactBytes: number;
}

export const DEFAULT_CACHE_POLICY: CachePolicy = {
  metadataTtlMs: 60 * 60 * 1000,
  maxArtifactBytes: 2 * 1024 * 1024 * 1024,
};

export class UpdateCache {
  constructor(
    private readonly root: string,
    private readonly policy: CachePolicy = DEFAULT_CACHE_POLICY,
  ) {}

  private get metaDir(): string {
    return join(this.root, 'metadata');
  }

  private get artifactDir(): string {
    return join(this.root, 'artifacts');
  }

  async getMetadata(key: string): Promise<string | null> {
    const path = join(this.metaDir, `${sanitize(key)}.json`);

    if (!existsSync(path)) {return null;}

    try {
      const raw = JSON.parse(await readFile(path, 'utf-8')) as { at: number; body: string };

      if (Date.now() - raw.at > this.policy.metadataTtlMs) {
        await rm(path, { force: true });

        return null;
      }

      return raw.body;
    } catch {
      return null;
    }
  }

  async setMetadata(key: string, body: string): Promise<void> {
    await mkdir(this.metaDir, { recursive: true });
    await writeFile(join(this.metaDir, `${sanitize(key)}.json`), JSON.stringify({ at: Date.now(), body }));
  }

  /** Evict oldest artifacts until total size fits the budget. Returns freed bytes. */
  async enforceArtifactBudget(): Promise<number> {
    if (!existsSync(this.artifactDir)) {return 0;}
    const entries = await readdir(this.artifactDir);

    const sized = await Promise.all(
      entries.map(async (name) => {
        const p = join(this.artifactDir, name);

        try {
          const s = await stat(p);

          return { name, path: p, size: s.size, mtime: s.mtimeMs };
        } catch {
          return null;
        }
      }),
    );

    const files = sized.filter((f): f is NonNullable<typeof f> => f !== null).sort((a, b) => a.mtime - b.mtime);
    let total = files.reduce((n, f) => n + f.size, 0);
    let freed = 0;

    for (const f of files) {
      if (total <= this.policy.maxArtifactBytes) {break;}
      await rm(f.path, { force: true });
      total -= f.size;
      freed += f.size;
    }

    return freed;
  }

  /**
   * Post-update cleanup: delete everything in `tempDir`, keep only the
   * listed retain paths in the artifact dir.
   */
  async cleanupAfterUpdate(tempDir: string, retainArtifactNames: string[]): Promise<void> {
    await rm(tempDir, { recursive: true, force: true });

    if (!existsSync(this.artifactDir)) {return;}
    const entries = await readdir(this.artifactDir);
    await Promise.all(
      entries
        .filter((n) => !retainArtifactNames.includes(n))
        .map((n) => rm(join(this.artifactDir, n), { force: true, recursive: true })),
    );
  }
}

function sanitize(key: string): string {
  return key.replace(/[^A-Za-z0-9._-]/g, '_').slice(0, 128);
}
