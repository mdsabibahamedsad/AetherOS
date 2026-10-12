/**
 * Fake Update Server — test harness (spec §66).
 *
 * In-process HTTP server supporting every harness scenario:
 *   no-update | update-available | corrupt-artifact | invalid-signature |
 *   interrupted-download | slow-download | network-failure |
 *   revoked-release | mandatory-update | rollback | migration-failure
 *
 * No dependencies beyond node:http. Used by vitest integration tests.
 */

import { createHash, generateKeyPairSync, sign } from 'node:crypto';
import { createServer, type IncomingMessage, type Server, type ServerResponse } from 'node:http';

import type { ArtifactInfo, UpdateManifest } from './types';

export type HarnessScenario =
  | 'no-update'
  | 'update-available'
  | 'corrupt-artifact'
  | 'invalid-signature'
  | 'interrupted-download'
  | 'slow-download'
  | 'network-failure'
  | 'revoked-release'
  | 'mandatory-update';

export interface HarnessOptions {
  version?: string;
  currentVersion?: string;
  scenario?: HarnessScenario;
  slowChunkMs?: number;
}

export class FakeUpdateServer {
  private server: Server | null = null;
  private artifactBytes: Buffer;
  readonly publicKey: string;
  private readonly privateKey: string;
  readonly artifactSha256: string;
  readonly artifactSignature: string;
  manifest: UpdateManifest;
  scenario: HarnessScenario;

  constructor(private readonly options: HarnessOptions = {}) {
    const { publicKey, privateKey } = generateKeyPairSync('rsa', {
      modulusLength: 2048,
      publicKeyEncoding: { type: 'spki', format: 'pem' },
      privateKeyEncoding: { type: 'pkcs8', format: 'pem' },
    });

    this.publicKey = publicKey;
    this.privateKey = privateKey;
    this.scenario = options.scenario ?? 'update-available';

    this.artifactBytes = Buffer.from(`fake-aetheros-artifact-${Date.now()}-`.padEnd(4096, 'x'));
    this.artifactSha256 = createHash('sha256').update(this.artifactBytes).digest('hex');
    this.artifactSignature = sign('sha256', this.artifactBytes, this.privateKey).toString('base64');

    const version = options.version ?? '1.2.0';

    const artifact: ArtifactInfo = {
      platform: 'linux',
      architecture: 'x64',
      version,
      buildId: 'test-build',
      sourceCommit: 'abc123',
      sha256: this.artifactSha256,
      size: this.artifactBytes.length,
      signature: this.artifactSignature,
      url: '', // filled on listen()
      provenance: { builder: 'AetherOS', buildTimestamp: new Date().toISOString(), buildWorkflow: 'test', dependencies: [] },
      packaging: 'appimage',
    };

    this.manifest = {
      product: 'AetherOS',
      version,
      channel: 'stable',
      releaseId: 'test-release',
      commit: 'abc123',
      platforms: { 'linux-x64': artifact },
      minimumVersion: options.currentVersion ?? '1.0.0',
      artifacts: [artifact],
      releaseNotes: 'Test release',
      security: { classification: this.scenario === 'mandatory-update' ? 'security-critical' : 'normal' },
      rollout: { percentage: 100, startDate: new Date().toISOString(), killSwitch: this.scenario === 'revoked-release' },
      protocolVersion: 1,
      timestamp: new Date().toISOString(),
      signature: '',
    };
    this.manifest.signature = sign('sha256', Buffer.from(canonical(this.manifest)), this.privateKey).toString('base64');

    if (this.scenario === 'invalid-signature') {
      this.manifest.signature = Buffer.from('tampered').toString('base64');
    }

    if (this.scenario === 'corrupt-artifact') {
      this.artifactBytes = Buffer.from('CORRUPTED!!!');
    }
  }

  async listen(port = 0): Promise<string> {
    const base = await new Promise<string>((resolve) => {
      this.server = createServer((req, res) => void this.handle(req, res));
      this.server.listen(port, '127.0.0.1', () => {
        const addr = this.server!.address();
        const p = typeof addr === 'object' && addr ? addr.port : port;
        const url = `http://127.0.0.1:${p}`;

        // Manifest advertises https in prod; tests rewrite to the harness URL.
        for (const a of this.manifest.artifacts) {a.url = `${url}/artifact.bin`;}
        this.manifest.platforms['linux-x64'].url = `${url}/artifact.bin`;
        resolve(url);
      });
    });

    return base;
  }

  async close(): Promise<void> {
    await new Promise<void>((resolve) => this.server?.close(() => resolve()) ?? resolve());
    this.server = null;
  }

  private async handle(req: IncomingMessage, res: ServerResponse): Promise<void> {
    if (this.scenario === 'network-failure') {
      res.destroy();

      return;
    }

    if (req.url?.startsWith('/updates/')) {
      if (this.scenario === 'no-update') {
        res.writeHead(404).end('no update');

        return;
      }

      res.writeHead(200, { 'content-type': 'application/json' }).end(JSON.stringify(this.manifest));

      return;
    }

    if (req.url === '/artifact.bin') {
      const bytes = this.artifactBytes;

      if (this.scenario === 'interrupted-download') {
        res.writeHead(200, { 'content-length': bytes.length });
        res.write(bytes.subarray(0, Math.floor(bytes.length / 2)));
        res.destroy();

        return;
      }

      if (this.scenario === 'slow-download') {
        res.writeHead(200, { 'content-length': bytes.length });
        const delay = this.options.slowChunkMs ?? 5;

        for (let i = 0; i < bytes.length; i += 256) {
          res.write(bytes.subarray(i, i + 256));
          await new Promise((r) => setTimeout(r, delay));
        }

        res.end();

        return;
      }

      // Range support for resume tests.
      const range = req.headers.range;

      if (range) {
        const m = /bytes=(\d+)-/.exec(range);
        const start = m ? parseInt(m[1], 10) : 0;
        res.writeHead(206, {
          'content-range': `bytes ${start}-${bytes.length - 1}/${bytes.length}`,
          'content-length': bytes.length - start,
        });
        res.end(bytes.subarray(start));

        return;
      }

      res.writeHead(200, { 'content-length': bytes.length });
      res.end(bytes);

      return;
    }

    res.writeHead(404).end('not found');
  }
}

function canonical(manifest: UpdateManifest): string {
  const { signature: _s, ...rest } = manifest;

  return stableStringify(rest);
}

function stableStringify(value: unknown): string {
  if (value === null || typeof value !== 'object') {return JSON.stringify(value);}

  if (Array.isArray(value)) {return `[${(value as unknown[]).map(stableStringify).join(',')}]`;}

  const entries = Object.entries(value as Record<string, unknown>)
    .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
    .map(([k, v]) => `${JSON.stringify(k)}:${stableStringify(v)}`);

  return `{${entries.join(',')}}`;
}
