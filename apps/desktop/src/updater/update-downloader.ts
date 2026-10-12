/**
 * Update Downloader — resumable, pausable, cancellable artifact fetch.
 *
 * Spec (§15–§17, §51–§53): HTTP Range resume, final hash check, pause /
 * resume / cancel, disk-space preflight, bounded buffering (stream to
 * disk, never hold the whole artifact in memory).
 */

import { createWriteStream, existsSync, renameSync } from 'node:fs';
import { mkdir, rename, stat } from 'node:fs/promises';
import { basename, dirname } from 'node:path';

import type { ArtifactInfo } from './types';
import { sha256File } from './update-verifier';

export interface DownloadSnapshot {
  bytesDownloaded: number;
  bytesTotal: number;
  percent: number;
  speedBps: number;
  etaSec: number;
}

export type DownloadListener = (snapshot: DownloadSnapshot) => void;

export interface DownloaderOptions {
  /** Directory for staged downloads. */
  stagingDir: string;
  /** Fail before downloading if free space < size * factor. */
  diskMarginFactor?: number;
  /** Free-space probe (bytes). Default returns Infinity (skip). */
  getFreeBytes?: (dir: string) => Promise<number>;
  /** Extra headers, e.g. auth for enterprise channels. */
  headers?: Record<string, string>;
  /** AbortSignal for cancellation. */
  signal?: AbortSignal;
  fetchImpl?: typeof fetch;
  onProgress?: DownloadListener;
}

export class ResumableDownloader {
  private paused = false;
  private aborted = false;

  pause(): void {
    this.paused = true;
  }

  resume(): void {
    this.paused = false;
  }

  cancel(): void {
    this.aborted = true;
    this.paused = false;
  }

  get isPaused(): boolean {
    return this.paused;
  }

  async download(artifact: ArtifactInfo, options: DownloaderOptions): Promise<string> {
    const { stagingDir, fetchImpl = fetch, headers = {}, signal, onProgress } = options;
    const margin = options.diskMarginFactor ?? 1.5;

    await mkdir(stagingDir, { recursive: true });

    if (options.getFreeBytes) {
      const free = await options.getFreeBytes(stagingDir);

      if (free < artifact.size * margin) {
        throw insufficientDisk(artifact.size, free);
      }
    }

    const fileName = safeFileName(artifact.url) ?? `aetheros-update-${Date.now()}.bin`;
    const partPath = `${stagingDir}/${fileName}.part`;
    const finalPath = `${stagingDir}/${fileName}`;

    let start = 0;

    if (existsSync(partPath)) {
      start = (await stat(partPath)).size;

      if (start > artifact.size) {start = 0;} // corrupt partial; restart

      if (start === artifact.size) {
        // Already fully downloaded — verify hash before accepting.
        const digest = await sha256File(partPath);

        if (digest.toLowerCase() === artifact.sha256.toLowerCase()) {
          await rename(partPath, finalPath);

          return finalPath;
        }

        start = 0;
      }
    }

    const reqHeaders: Record<string, string> = {
      Accept: 'application/octet-stream',
      ...headers,
    };

    if (start > 0) {reqHeaders.Range = `bytes=${start}-`;}

    const response = await fetchImpl(artifact.url, { headers: reqHeaders, signal });

    if (start > 0 && response.status === 200) {
      // Server ignored Range — restart from scratch to avoid corrupt file.
      start = 0;
    } else if (!response.ok && response.status !== 206) {
      throw new Error(`Download failed: HTTP ${response.status}`);
    }

    const total = totalFromResponse(response, artifact.size, start);
    let downloaded = start;
    const t0 = Date.now();

    await new Promise<void>((resolve, reject) => {
      const out = createWriteStream(partPath, { flags: start > 0 ? 'a' : 'w' });
      const reader = (response.body as ReadableStream<Uint8Array> | null)?.getReader();

      if (!reader) {
        out.close();
        reject(new Error('Empty response body'));

        return;
      }

      const pump = async (): Promise<void> => {
        try {
          for (;;) {
            if (this.aborted) {throw new Error('Download cancelled');}

            while (this.paused && !this.aborted) {
              await sleep(100);
            }

            const { done, value } = await reader.read();

            if (done) {break;}

            if (this.aborted) {throw new Error('Download cancelled');}
            await writeChunk(out, value);
            downloaded += value.length;
            onProgress?.(snapshot(downloaded, total, t0));
          }

          out.end(() => resolve());
        } catch (e) {
          out.close();
          reject(e);
        }
      };

      if (signal) {
        const onAbort = () => {
          this.aborted = true;
        };

        if (signal.aborted) {onAbort();}
        else {signal.addEventListener('abort', onAbort, { once: true });}
      }

      void pump();
    });

    const digest = await sha256File(partPath);

    if (digest.toLowerCase() !== artifact.sha256.toLowerCase()) {
      throw new Error('HASH_MISMATCH: downloaded artifact does not match manifest');
    }

    if (existsSync(finalPath)) {
      // Never overwrite in place — rename atomically via temp name.
      await rename(partPath, `${finalPath}.${Date.now()}.new`);

      return `${finalPath}.${Date.now()}.new`;
    }

    renameSync(partPath, finalPath);

    return finalPath;
  }
}

function snapshot(downloaded: number, total: number, t0: number): DownloadSnapshot {
  const elapsed = Math.max((Date.now() - t0) / 1000, 0.001);
  const speed = downloaded / elapsed;

  return {
    bytesDownloaded: downloaded,
    bytesTotal: total,
    percent: total > 0 ? (downloaded / total) * 100 : 0,
    speedBps: speed,
    etaSec: speed > 0 && total > downloaded ? (total - downloaded) / speed : 0,
  };
}

function totalFromResponse(response: Response, manifestSize: number, start: number): number {
  const len = response.headers.get('content-length');

  if (len) {
    const n = parseInt(len, 10);

    if (!Number.isNaN(n)) {return response.status === 206 ? start + n : n;}
  }

  return manifestSize;
}

function safeFileName(url: string): string | null {
  try {
    const name = basename(new URL(url).pathname);

    if (!name || name === '/' || name.includes('..')) {return null;}

    return name.replace(/[^A-Za-z0-9._-]/g, '_');
  } catch {
    return null;
  }
}

function insufficientDisk(required: number, free: number): Error {
  const e = new Error(`INSUFFICIENT_DISK: need ~${required} bytes, only ${free} free`);
  (e as NodeJS.ErrnoException).code = 'INSUFFICIENT_DISK';

  return e;
}

function writeChunk(stream: { write(c: Uint8Array, cb: (e?: Error | null) => void): void }, chunk: Uint8Array): Promise<void> {
  return new Promise((resolve, reject) => {
    stream.write(chunk, (e) => (e ? reject(e) : resolve()));
  });
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

export { dirname as _dirnameForIsolation };
