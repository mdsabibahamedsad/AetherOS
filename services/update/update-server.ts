/**
 * Update Server Service
 * Handles manifest publishing, artifact serving, and rollout management
 */

import * as fs from 'node:fs/promises';
import * as path from 'node:path';
import * as crypto from 'node:crypto';
import { EventEmitter } from 'node:events';

import {
  UpdateManifest,
  ArtifactInfo,
  PackagingFormat,
  ReleaseChannel,
  Platform,
  Architecture,
  RolloutPolicy,
  SecurityInfo,
  ProvenanceInfo,
} from '../../apps/desktop/src/updater/types';
import { parseSemanticVersion, compareVersions } from '../../apps/desktop/src/updater/semver';

interface ReleaseRecord {
  manifest: UpdateManifest;
  artifacts: Map<string, Buffer>;
  createdAt: string;
  status: 'draft' | 'published' | 'revoked' | 'archived';
  promotedFrom?: string;
}

interface ChannelConfig {
  channel: ReleaseChannel;
  rolloutPolicy: RolloutPolicy;
  autoPromote: boolean;
  requiredApprovals: number;
}

export class UpdateServer extends EventEmitter {
  private storagePath: string;
  private releases: Map<string, ReleaseRecord> = new Map();
  private channels: Map<ReleaseChannel, ChannelConfig> = new Map();
  private publicKey!: string;
  private privateKey!: string;

  constructor(storagePath: string = './update-storage') {
    super();
    this.storagePath = storagePath;
    this.initializeChannels();
    this.loadKeys();
  }

  private initializeChannels(): void {
    const defaultChannels: ChannelConfig[] = [
      {
        channel: 'nightly',
        rolloutPolicy: {
          percentage: 100,
          startDate: new Date().toISOString(),
        },
        autoPromote: false,
        requiredApprovals: 0,
      },
      {
        channel: 'dev',
        rolloutPolicy: {
          percentage: 100,
          startDate: new Date().toISOString(),
        },
        autoPromote: false,
        requiredApprovals: 1,
      },
      {
        channel: 'alpha',
        rolloutPolicy: {
          percentage: 25,
          startDate: new Date().toISOString(),
        },
        autoPromote: false,
        requiredApprovals: 1,
      },
      {
        channel: 'beta',
        rolloutPolicy: {
          percentage: 10,
          startDate: new Date().toISOString(),
        },
        autoPromote: false,
        requiredApprovals: 2,
      },
      {
        channel: 'stable',
        rolloutPolicy: {
          percentage: 5,
          startDate: new Date().toISOString(),
        },
        autoPromote: false,
        requiredApprovals: 3,
      },
      {
        channel: 'enterprise',
        rolloutPolicy: {
          percentage: 100,
          startDate: new Date().toISOString(),
        },
        autoPromote: false,
        requiredApprovals: 1,
      },
    ];

    for (const config of defaultChannels) {
      this.channels.set(config.channel, config);
    }
  }

  private loadKeys(): void {
    // Production: load PEM keys from env-provided paths; ephemeral only for
    // local dev/test. NEVER ship ephemeral keys to production.
    const pubPath = process.env.AETHEROS_UPDATE_PUBKEY_PATH;
    const privPath = process.env.AETHEROS_UPDATE_PRIVKEY_PATH;
    if (pubPath && privPath) {
      const { readFileSync } = require('node:fs') as typeof import('node:fs');
      this.publicKey = readFileSync(pubPath, 'utf-8');
      this.privateKey = readFileSync(privPath, 'utf-8');
      return;
    }
    if (process.env.NODE_ENV === 'production') {
      throw new Error('AETHEROS_UPDATE_PUBKEY_PATH/PRIVKEY_PATH required in production');
    }
    const { publicKey, privateKey } = crypto.generateKeyPairSync('rsa', {
      modulusLength: 2048,
      publicKeyEncoding: { type: 'spki', format: 'pem' },
      privateKeyEncoding: { type: 'pkcs8', format: 'pem' },
    });
    this.publicKey = publicKey;
    this.privateKey = privateKey;
  }

  /** Public key for clients / out-of-band distribution. */
  getPublicKey(): string {
    return this.publicKey;
  }

  /** Verify an artifact's signature with the server public key. */
  verifyArtifactSignature(buffer: Buffer, signatureB64: string): boolean {
    try {
      return crypto.verify('sha256', buffer, this.publicKey, Buffer.from(signatureB64, 'base64'));
    } catch {
      return false;
    }
  }

  /**
   * Create a new release
   */
  async createRelease(
    version: string,
    channel: ReleaseChannel,
    artifacts: Map<string, Buffer>,
    commit: string,
    provenance: ProvenanceInfo,
    security: SecurityInfo = { classification: 'normal' },
    releaseNotes: string = ''
  ): Promise<UpdateManifest> {
    // Validate version
    const parsed = parseSemanticVersion(version);

    // Create release ID
    const releaseId = crypto.randomBytes(16).toString('hex');

    // Build platform artifacts map
    const platformArtifacts: Record<string, ArtifactInfo> = {};
    const artifactList: ArtifactInfo[] = [];

    for (const [key, buffer] of artifacts) {
      const [platform, arch] = key.split('-');
      const sha256 = crypto.createHash('sha256').update(buffer).digest('hex');
      const signature = this.signBuffer(buffer);

      const artifact: ArtifactInfo = {
        platform: platform as Platform,
        architecture: arch as Architecture,
        version,
        buildId: crypto.randomBytes(8).toString('hex'),
        sourceCommit: commit,
        sha256,
        size: buffer.length,
        signature,
        url: `${this.getBaseUrl()}/${channel}/${platform}-${arch}/${version}/${key}`,
        provenance,
        packaging: this.getPackagingFormat(platform as Platform),
      };

      platformArtifacts[key] = artifact;
      artifactList.push(artifact);
    }

    // Get channel config
    const channelConfig = this.channels.get(channel)!;

    // Create manifest
    const manifest: UpdateManifest = {
      product: 'AetherOS',
      version,
      channel,
      releaseId,
      commit,
      platforms: platformArtifacts,
      minimumVersion: this.getMinimumVersion(channel),
      artifacts: artifactList,
      releaseNotes,
      security,
      rollout: channelConfig.rolloutPolicy,
      protocolVersion: 1,
      timestamp: new Date().toISOString(),
      signature: '', // Will be filled after signing
    };

    // Sign manifest
    manifest.signature = this.signManifest(manifest);

    // Store release
    const record: ReleaseRecord = {
      manifest,
      artifacts,
      createdAt: new Date().toISOString(),
      status: 'draft',
    };

    this.releases.set(releaseId, record);
    await this.persistRelease(record);

    this.emit('release-created', { releaseId, version, channel });
    return manifest;
  }

  /**
   * Publish a release to a channel
   */
  async publishRelease(releaseId: string): Promise<void> {
    const record = this.releases.get(releaseId);
    if (!record) {
      throw new Error(`Release not found: ${releaseId}`);
    }

    if (record.status !== 'draft') {
      throw new Error(`Release already ${record.status}`);
    }

    // Validate release
    await this.validateRelease(record);

    // Update status
    record.status = 'published';
    await this.persistRelease(record);

    // Update channel rollout
    await this.updateChannelRollout(record.manifest.channel, record.manifest.releaseId);

    this.emit('release-published', { releaseId, version: record.manifest.version, channel: record.manifest.channel });
  }

  /**
   * Revoke a release
   */
  async revokeRelease(releaseId: string, reason: string): Promise<void> {
    const record = this.releases.get(releaseId);
    if (!record) {
      throw new Error(`Release not found: ${releaseId}`);
    }

    record.status = 'revoked';
    record.manifest.rollout.killSwitch = true;
    await this.persistRelease(record);

    this.emit('release-revoked', { releaseId, reason });
  }

  /**
   * Promote release to next channel
   */
  async promoteRelease(releaseId: string, targetChannel: ReleaseChannel): Promise<UpdateManifest> {
    const record = this.releases.get(releaseId);
    if (!record) {
      throw new Error(`Release not found: ${releaseId}`);
    }

    if (record.status !== 'published') {
      throw new Error(`Release not published`);
    }

    const channelOrder: ReleaseChannel[] = ['nightly', 'dev', 'alpha', 'beta', 'stable', 'enterprise'];
    const currentIndex = channelOrder.indexOf(record.manifest.channel);
    const targetIndex = channelOrder.indexOf(targetChannel);

    if (targetIndex <= currentIndex) {
      throw new Error(`Cannot promote to same or earlier channel`);
    }

    // Create new release in target channel
    const newManifest = await this.createRelease(
      record.manifest.version,
      targetChannel,
      record.artifacts,
      record.manifest.commit,
      record.manifest.artifacts[0].provenance,
      record.manifest.security,
      record.manifest.releaseNotes
    );

    const stored = this.releases.get(newManifest.releaseId);
    if (stored) {
      stored.promotedFrom = releaseId;
      await this.persistRelease(stored);
    }

    return newManifest;
  }

  /**
   * Get manifest for a channel/platform/architecture
   */
  async getManifest(channel: ReleaseChannel, platform: Platform, architecture: Architecture): Promise<UpdateManifest | null> {
    // Newest eligible published release for this channel (semver-descending).
    // Insertion order is oldest-first, so without sorting clients would pin
    // to the first-published release and never see newer ones (found by the
    // Master 89 rehearsal: 1.0.1-test.2 was published but A clients kept
    // receiving 1.0.1-test.1).
    const candidates = Array.from(this.releases.values())
      .filter((r) => r.status === 'published' && r.manifest.channel === channel && r.manifest.platforms[`${platform}-${architecture}`])
      .sort((a, b) => compareVersions(b.manifest.version, a.manifest.version));
    for (const record of candidates) {
      // Check rollout eligibility
      if (await this.checkRolloutEligibility(record.manifest, channel)) {
        return record.manifest;
      }
    }
    return null;
  }

  /**
   * Get artifact bytes for a published release.
   */
  async getArtifact(channel: ReleaseChannel, platform: Platform, architecture: Architecture, version: string): Promise<Buffer | null> {
    for (const record of this.releases.values()) {
      const m = record.manifest;
      if (record.status !== 'published') continue;
      if (m.channel !== channel || m.version !== version) continue;
      const buf = record.artifacts.get(`${platform}-${architecture}`);
      if (buf) return buf;
    }
    return null;
  }

  /**
   * Get a specific release manifest by releaseId (published or revoked).
   */
  getRelease(releaseId: string): UpdateManifest | null {
    return this.releases.get(releaseId)?.manifest ?? null;
  }

  /** Latest known-good (published, not kill-switched) manifest per channel. */
  getPreviousKnownGoodManifest(channel: ReleaseChannel): UpdateManifest | null {
    return this.getPreviousKnownGood(channel)?.manifest ?? null;
  }

  /**
   * Configure channel rollout
   */
  async configureRollout(channel: ReleaseChannel, rollout: RolloutPolicy): Promise<void> {
    const config = this.channels.get(channel);
    if (!config) {
      throw new Error(`Channel not found: ${channel}`);
    }

    config.rolloutPolicy = rollout;
    await this.persistChannelConfig(channel, config);

    this.emit('rollout-configured', { channel, rollout });
  }

  /**
   * Emergency rollback - stop rollout and promote previous version
   */
  async emergencyRollback(channel: ReleaseChannel, reason: string): Promise<void> {
    const config = this.channels.get(channel);
    if (!config) {
      throw new Error(`Channel not found: ${channel}`);
    }

    // Kill current rollout
    config.rolloutPolicy.killSwitch = true;
    await this.persistChannelConfig(channel, config);

    // Find previous known-good release
    const previousRelease = this.getPreviousKnownGood(channel);
    if (previousRelease) {
      // Republish previous release
      previousRelease.manifest.rollout.percentage = 100;
      previousRelease.manifest.rollout.killSwitch = false;
      await this.publishRelease(previousRelease.manifest.releaseId);
    }

    this.emit('emergency-rollback', { channel, reason });
  }

  /**
   * Get rollout status
   */
  getRolloutStatus(channel: ReleaseChannel): RolloutPolicy | null {
    const config = this.channels.get(channel);
    return config?.rolloutPolicy || null;
  }

  // Private methods

  private async validateRelease(record: ReleaseRecord): Promise<void> {
    // Verify all artifacts exist
    for (const artifact of record.manifest.artifacts) {
      const key = `${artifact.platform}-${artifact.architecture}`;
      if (!record.artifacts.has(key)) {
        throw new Error(`Missing artifact: ${key}`);
      }
    }

    // Verify signatures
    if (!record.manifest.signature) {
      throw new Error('Manifest not signed');
    }

    if (!this.verifyManifestSignature(record.manifest)) {
      throw new Error('Invalid manifest signature');
    }

    // Verify artifact signatures (VERIFY — never re-sign and compare)
    for (const artifact of record.manifest.artifacts) {
      const key = `${artifact.platform}-${artifact.architecture}`;
      const buffer = record.artifacts.get(key);
      if (!buffer) {
        throw new Error(`Missing artifact bytes: ${key}`);
      }
      if (!this.verifyArtifactSignature(buffer, artifact.signature)) {
        throw new Error(`Artifact signature mismatch: ${key}`);
      }
      const digest = crypto.createHash('sha256').update(buffer).digest('hex');
      if (digest.toLowerCase() !== artifact.sha256.toLowerCase()) {
        throw new Error(`Artifact hash mismatch: ${key}`);
      }
    }
  }

  private async updateChannelRollout(channel: ReleaseChannel, releaseId: string): Promise<void> {
    // Update rollout policy for this release
    const config = this.channels.get(channel);
    if (config) {
      config.rolloutPolicy = {
        ...config.rolloutPolicy,
        // In production, this would track individual release rollout
      };
      await this.persistChannelConfig(channel, config);
    }
  }

  private async checkRolloutEligibility(manifest: UpdateManifest, channel: ReleaseChannel): Promise<boolean> {
    if (manifest.rollout.killSwitch) return false;

    const percentage = manifest.rollout.percentage;
    if (percentage >= 100) return true;

    // Use consistent hashing for cohort assignment
    // In production, this would use device ID or similar
    const hash = crypto.createHash('sha256').update(`${manifest.releaseId}-${channel}`).digest('hex');
    const bucket = parseInt(hash.slice(0, 8), 16) % 100;

    return bucket < percentage;
  }

  private getPreviousKnownGood(channel: ReleaseChannel): ReleaseRecord | null {
    const channelReleases = Array.from(this.releases.values())
      .filter(r => r.manifest.channel === channel && r.status === 'published')
      .sort((a, b) => compareVersions(b.manifest.version, a.manifest.version));

    return channelReleases[1] || null;
  }

  private signManifest(manifest: UpdateManifest): string {
    const { signature, ...manifestWithoutSig } = manifest;
    return crypto.sign('sha256', Buffer.from(stableStringify(manifestWithoutSig)), this.privateKey).toString('base64');
  }

  private verifyManifestSignature(manifest: UpdateManifest): boolean {
    const { signature, ...manifestWithoutSig } = manifest;
    try {
      return crypto.verify(
        'sha256',
        Buffer.from(stableStringify(manifestWithoutSig)),
        this.publicKey,
        Buffer.from(signature, 'base64'),
      );
    } catch {
      return false;
    }
  }

  private signBuffer(buffer: Buffer): string {
    return crypto.sign('sha256', buffer, this.privateKey).toString('base64');
  }

  private getBaseUrl(): string {
    return 'https://releases.aetheros.com';
  }

  private getPackagingFormat(platform: Platform): PackagingFormat {
    const formats: Record<Platform, PackagingFormat> = {
      win32: 'nsis',
      darwin: 'dmg',
      linux: 'appimage',
      web: 'web',
      ios: 'ipa',
      android: 'apk',
    };
    return formats[platform] || 'unknown';
  }

  private getMinimumVersion(channel: ReleaseChannel): string {
    // In production, this would be configurable per channel
    return '1.0.0';
  }

  private async persistRelease(record: ReleaseRecord): Promise<void> {
    await fs.mkdir(this.storagePath, { recursive: true });
    const filePath = path.join(this.storagePath, `${record.manifest.releaseId}.json`);
    const data = {
      manifest: record.manifest,
      createdAt: record.createdAt,
      status: record.status,
      promotedFrom: record.promotedFrom,
    };
    await fs.writeFile(filePath, JSON.stringify(data, null, 2));
  }

  private async persistChannelConfig(channel: ReleaseChannel, config: ChannelConfig): Promise<void> {
    await fs.mkdir(this.storagePath, { recursive: true });
    const filePath = path.join(this.storagePath, `channel-${channel}.json`);
    await fs.writeFile(filePath, JSON.stringify(config, null, 2));
  }

  async loadFromStorage(): Promise<void> {
    try {
      const files = await fs.readdir(this.storagePath);
      for (const file of files) {
        if (file.endsWith('.json') && !file.startsWith('channel-')) {
          const data = JSON.parse(await fs.readFile(path.join(this.storagePath, file), 'utf-8'));
          this.releases.set(data.manifest.releaseId, {
            manifest: data.manifest,
            artifacts: new Map(), // Artifacts stored separately
            createdAt: data.createdAt,
            status: data.status,
            promotedFrom: data.promotedFrom,
          });
        } else if (file.startsWith('channel-')) {
          const data = JSON.parse(await fs.readFile(path.join(this.storagePath, file), 'utf-8'));
          this.channels.set(data.channel, data);
        }
      }
    } catch {
      // Storage not initialized
    }
  }
}

interface ArtifactUpload {
  platform: Platform;
  architecture: Architecture;
  buffer: Buffer;
  packaging: string;
}

interface ReleaseBuilder {
  version: string;
  channel: ReleaseChannel;
  artifacts: Map<string, ArtifactUpload>;
  commit: string;
  provenance: ProvenanceInfo;
  security: SecurityInfo;
  releaseNotes: string;
}

// --- HTTP endpoint layer (spec §27–§28) --------------------------------------
// Zero-dependency node:http router. TLS terminates at the reverse proxy;
// all artifact URLs served here MUST be https in production (enforced by
// requireHttpsBaseUrl). Endpoints:
//   GET /updates/{platform}/{arch}/{channel}          → latest manifest
//   GET /updates/{platform}/{arch}/{channel}/{version} → pinned manifest (same latest; version must match)
//   GET /updates/releases/{releaseId}                  → release manifest + status
//   GET /artifacts/{channel}/{version}/{platform}-{arch} → artifact bytes

export interface UpdateHttpOptions {
  baseUrl: string;
  requireHttps?: boolean;
}

const VALID_PLATFORM_ARCH = /^([a-z0-9]+)-([a-z0-9]+)$/;

export function createUpdateRequestHandler(server: UpdateServer, options: UpdateHttpOptions) {
  if (options.requireHttps !== false && !options.baseUrl.startsWith('https://')) {
    throw new Error('Update base URL must be https in production');
  }
  return async (req: { method?: string; url?: string }, res: {
    writeHead(s: number, h?: Record<string, string>): void;
    end(b?: string | Buffer): void;
  }) => {
    try {
      const url = new URL(req.url ?? '/', 'http://localhost');
      const parts = url.pathname.split('/').filter(Boolean);

      if (req.method === 'GET' && parts[0] === 'updates' && parts[1] === 'releases' && parts[2]) {
        const manifest = server.getRelease(parts[2]);
        if (!manifest) return json(res, 404, { error: 'release not found' });
        return json(res, 200, { manifest });
      }

      if (req.method === 'GET' && parts[0] === 'updates' && parts.length >= 4) {
        const [, platform, arch, channel, version] = parts;
        if (!VALID_PLATFORM_ARCH.test(`${platform}-${arch}`)) {
          return json(res, 400, { error: 'invalid platform/arch' });
        }
        const manifest = await server.getManifest(
          channel as ReleaseChannel, platform as Platform, arch as Architecture,
        );
        if (!manifest) return json(res, 404, { error: 'no published release for channel/platform' });
        if (version && manifest.version !== version) {
          return json(res, 404, { error: 'version not found on this channel' });
        }
        return json(res, 200, manifest);
      }

      if (req.method === 'GET' && parts[0] === 'artifacts' && parts.length === 4) {
        const [, channel, version, key] = parts;
        const dash = key.lastIndexOf('-');
        const platform = key.slice(0, dash) as Platform;
        const arch = key.slice(dash + 1) as Architecture;
        const buf = await server.getArtifact(channel as ReleaseChannel, platform, arch, version);
        if (!buf) return json(res, 404, { error: 'artifact not found' });
        res.writeHead(200, {
          'content-type': 'application/octet-stream',
          'content-length': String(buf.length),
          'cache-control': 'public, max-age=31536000, immutable',
        });
        res.end(buf);
        return;
      }

      if (req.method === 'GET' && parts[0] === 'health') {
        return json(res, 200, { ok: true });
      }

      return json(res, 404, { error: 'not found' });
    } catch (e) {
      return json(res, 500, { error: e instanceof Error ? e.message : 'internal error' });
    }
  };
}

function json(res: { writeHead(s: number, h?: Record<string, string>): void; end(b?: string): void }, status: number, body: unknown): void {
  res.writeHead(status, { 'content-type': 'application/json', 'cache-control': 'no-store' });
  res.end(JSON.stringify(body));
}

/** Canonical JSON: recursively sorted keys, all keys retained at every level. */
function stableStringify(value: unknown): string {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${(value as unknown[]).map(stableStringify).join(',')}]`;
  const entries = Object.entries(value as Record<string, unknown>)
    .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
    .map(([k, v]) => `${JSON.stringify(k)}:${stableStringify(v)}`);
  return `{${entries.join(',')}}`;
}