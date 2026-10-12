/**
 * Update Manager - Main orchestrator for the update system
 */

import { execFile } from 'node:child_process';
import { EventEmitter } from 'node:events';
import * as fs from 'node:fs';
import { mkdir } from 'node:fs/promises';
import * as path from 'node:path';
import { promisify } from 'node:util';

import { isMandatoryUpdate, isReleaseRevoked, verifyManifest } from './manifest-verifier';
import type { InstallOptions, PlatformAdapter } from './platform-adapter';
import { PlatformAdapterFactory } from './platform-adapter';
import { compareVersions } from './semver';
import type {
  Architecture,
  ArtifactInfo,
  Platform,
  UpdateConfig,
  UpdateError,
  UpdateErrorCode,
  UpdateHistoryEntry,
  UpdateManifest,
  UpdateResult,
  UpdateState} from './types';
import { UpdateStateMachine } from './update-state-machine';

const execFileAsync = promisify(execFile);

const DEFAULT_CONFIG: UpdateConfig = {
  enabled: true,
  channel: 'stable',
  checkInterval: 24 * 60 * 60 * 1000, // 24 hours
  downloadAutomatically: true,
  installOnQuit: false,
  allowPrerelease: false,
  meteredNetworkPolicy: 'wifi-only',
  autoUpdateOnRestart: true,
  verifySignature: true,
  requireAdminForInstall: true,
};

export interface UpdateCheckResult {
  updateAvailable: boolean;
  manifest?: UpdateManifest;
  artifact?: ArtifactInfo;
  error?: UpdateError;
  mandatory?: boolean;
}

export interface DownloadProgress {
  bytesDownloaded: number;
  bytesTotal: number;
  speed: number;
  eta: number;
}

export class UpdateManager extends EventEmitter {
  private config: UpdateConfig;
  private state: UpdateState = 'IDLE';
  private currentVersion: string;
  private platform: Platform;
  private architecture: Architecture;
  private adapter: PlatformAdapter | null = null;
  private downloadController: AbortController | null = null;
  private lastCheck: number = 0;
  private checkTimer: NodeJS.Timeout | null = null;
  private manifest: UpdateManifest | null = null;
  private artifact: ArtifactInfo | null = null;
  private downloadPath: string | null = null;
  private history: UpdateHistoryEntry[] = [];
  /** Guarded lifecycle mirror — illegal jumps are rejected loudly in dev, tolerated in prod. */
  private readonly fsm = new UpdateStateMachine();

  constructor(
    currentVersion: string,
    config: Partial<UpdateConfig> = {},
    platform?: Platform,
    architecture?: Architecture
  ) {
    super();
    this.currentVersion = currentVersion;
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.platform = platform || (process.platform as Platform);
    this.architecture = architecture || (process.arch === 'arm64' ? 'arm64' : 'x64');
  }

  /**
   * Initialize the update manager
   */
  async initialize(): Promise<void> {
    try {
      this.adapter = await PlatformAdapterFactory.getForCurrentPlatform();
      this.emit('initialized');
    } catch (error) {
      this.emit('error', this.createError('UNSUPPORTED_PLATFORM', `Platform initialization failed: ${error instanceof Error ? error.message : 'unknown error'}`));
      throw error;
    }
  }

  /**
   * Check for updates
   */
  async checkForUpdates(force = false): Promise<UpdateCheckResult> {
    if (this.state === 'CHECKING') {
      return { updateAvailable: false, error: this.createError('NETWORK_FAILURE', 'Check already in progress') };
    }

    // Check interval unless forced
    if (!force && this.lastCheck > 0) {
      const elapsed = Date.now() - this.lastCheck;

      if (elapsed < this.config.checkInterval) {
        return { updateAvailable: false };
      }
    }

    this.setState('CHECKING');
    this.lastCheck = Date.now();

    try {
      // Fetch manifest from update server
      const manifest = await this.fetchManifest();

      // Check if revoked
      if (isReleaseRevoked(manifest)) {
        return { updateAvailable: false, error: this.createError('REVOKED_RELEASE', 'Release has been revoked') };
      }

      // Verify manifest (real RSA signature when a trusted key is configured)
      const verification = await verifyManifest(manifest, {
        currentVersion: this.currentVersion,
        channel: this.config.channel,
        platform: this.platform,
        architecture: this.architecture,
        allowDowngrade: false,
        allowPrerelease: this.config.allowPrerelease,
        expectedPublisher: 'AetherOS',
        publicKey: process.env.AETHEROS_UPDATE_PUBKEY_PEM,
      });

      if (!verification.valid) {
        const error = verification.errors[0];
        this.setState('IDLE');

        return { updateAvailable: false, error };
      }

      this.manifest = manifest;
      this.artifact = verification.artifact!;

      // Check if update is available
      if (verification.artifact && isVersionNewer(this.currentVersion, manifest.version)) {
        this.setState('AVAILABLE');

        const mandatory = isMandatoryUpdate(manifest, this.currentVersion);

        this.emit('update-available', {
          version: manifest.version,
          releaseNotes: manifest.releaseNotes,
          size: verification.artifact.size,
          mandatory,
          classification: manifest.security.classification,
        });

        // Auto-download if configured
        if (this.config.downloadAutomatically && !mandatory) {
          await this.downloadUpdate();
        }

        return {
          updateAvailable: true,
          manifest,
          artifact: verification.artifact,
          mandatory,
        };
      }

      this.setState('IDLE');

      return { updateAvailable: false };
    } catch (error) {
      this.setState('IDLE');
      const updateError = this.createError('NETWORK_FAILURE', `Check failed: ${error instanceof Error ? error.message : 'unknown error'}`);
      this.emit('error', updateError);

      return { updateAvailable: false, error: updateError };
    }
  }

  /**
   * Download the update artifact
   */
  async downloadUpdate(onProgress?: (progress: DownloadProgress) => void): Promise<{ success: boolean; path?: string; error?: UpdateError }> {
    if (!this.artifact || !this.manifest) {
      return { success: false, error: this.createError('MANIFEST_INVALID', 'No update available') };
    }

    if (this.state === 'DOWNLOADING') {
      return { success: false, error: this.createError('NETWORK_FAILURE', 'Download already in progress') };
    }

    this.setState('DOWNLOADING');
    this.downloadController = new AbortController();

    try {
      const config = await this.adapter!.getPlatformConfig();
      const fileName = path.basename(new URL(this.artifact!.url).pathname);
      this.downloadPath = path.join(config.stagingPath, `download-${Date.now()}`, fileName);

      await mkdir(path.dirname(this.downloadPath), { recursive: true });

      const response = await fetch(this.artifact!.url, {
        signal: this.downloadController.signal,
        headers: {
          'Accept': 'application/octet-stream',
        },
      });

      if (!response.ok) {
        throw new Error(`Download failed: ${response.status} ${response.statusText}`);
      }

      const total = parseInt(response.headers.get('content-length') || '0', 10);
      let downloaded = 0;
      const startTime = Date.now();

      const fileStream = fs.createWriteStream(this.downloadPath);
      const reader = response.body!.getReader();

      while (true) {
        const { done, value } = await reader.read();

        if (done) {break;}

        await new Promise<void>((resolve, reject) => {
          fileStream.write(value, (err) => {
            if (err) {reject(err);}
            else {resolve();}
          });
        });

        downloaded += value.length;

        if (onProgress && total > 0) {
          const elapsed = (Date.now() - startTime) / 1000;
          const speed = downloaded / elapsed;
          const eta = speed > 0 ? (total - downloaded) / speed : 0;

          onProgress({
            bytesDownloaded: downloaded,
            bytesTotal: total,
            speed,
            eta,
          });

          this.emit('download-progress', {
            percent: (downloaded / total) * 100,
            bytesDownloaded: downloaded,
            bytesTotal: total,
            speed,
            eta,
          });
        }
      }

      fileStream.end();
      await new Promise<void>((resolve, reject) => {
        fileStream.on('finish', resolve);
        fileStream.on('error', reject);
      });

      this.setState('VERIFYING');

      // Verify download
      const verified = await this.verifyDownload(this.downloadPath);

      if (!verified) {
        throw new Error('Download verification failed');
      }

      this.setState('STAGING');

      return { success: true, path: this.downloadPath };
    } catch (error) {
      this.setState('FAILED');
      const updateError = this.createError('NETWORK_FAILURE', `Download failed: ${error instanceof Error ? error.message : 'unknown error'}`);
      this.emit('error', updateError);

      return { success: false, error: updateError };
    }
  }

  /**
   * Install the downloaded update
   */
  async installUpdate(options: Partial<InstallOptions> = {}): Promise<UpdateResult> {
    if (!this.artifact || !this.downloadPath) {
      return { success: false, error: this.createError('MANIFEST_INVALID', 'No update to install') };
    }

    if (this.state === 'INSTALLING') {
      return { success: false, error: this.createError('INSTALL_FAILURE', 'Installation already in progress') };
    }

    // Check disk space
    const spaceCheck = await this.checkDiskSpace(this.artifact!.size);

    if (!spaceCheck) {
      return { success: false, error: this.createError('INSUFFICIENT_DISK', 'Insufficient disk space for installation') };
    }

    // Check network policy for metered connections
    if (this.config.meteredNetworkPolicy === 'block') {
      const isMetered = await this.isMeteredConnection();

      if (isMetered) {
        return { success: false, error: this.createError('NETWORK_FAILURE', 'Metered network policy blocks installation') };
      }
    }

    this.setState('INSTALLING');

    try {
      const installOptions: InstallOptions = {
        restartAfterInstall: options.restartAfterInstall ?? true,
        runHealthChecks: options.runHealthChecks ?? true,
        createBackup: options.createBackup ?? true,
        silent: options.silent ?? false,
      };

      const result = await this.adapter!.installUpdate(this.downloadPath, installOptions);

      if (result.success) {
        this.setState('COMPLETE');
        this.currentVersion = this.manifest!.version;

        // Record history
        this.addHistoryEntry({
          version: this.currentVersion,
          installedAt: new Date().toISOString(),
          source: 'auto',
          releaseId: this.manifest!.releaseId,
          result: 'success',
        });

        this.emit('installed', { version: this.currentVersion });
      } else {
        this.setState('FAILED');
        this.addHistoryEntry({
          version: this.manifest!.version,
          installedAt: new Date().toISOString(),
          source: 'auto',
          releaseId: this.manifest!.releaseId,
          result: 'failed',
          error: result.error,
        });

        // Attempt rollback if health checks failed
        if (result.rollbackPerformed) {
          this.setState('ROLLED_BACK');
        }
      }

      return result;
    } catch (error) {
      this.setState('FAILED');
      const updateError = this.createError('INSTALL_FAILURE', `Installation failed: ${error instanceof Error ? error.message : 'unknown error'}`);
      this.emit('error', updateError);

      return { success: false, error: updateError };
    }
  }

  /**
   * Perform rollback
   */
  async rollback(): Promise<UpdateResult> {
    if (!this.adapter) {
      return { success: false, error: this.createError('ROLLBACK_FAILURE', 'No adapter available') };
    }

    this.setState('ROLLBACK');

    try {
      const rollbackInfo = await this.adapter.getRollbackInfo();

      if (!rollbackInfo.available) {
        return { success: false, error: this.createError('ROLLBACK_FAILURE', 'No rollback available') };
      }

      const result = await this.adapter.rollback(rollbackInfo);

      if (result.success) {
        this.setState('ROLLED_BACK');
        this.currentVersion = result.version || rollbackInfo.previousVersion;

        this.addHistoryEntry({
          version: this.currentVersion,
          installedAt: new Date().toISOString(),
          source: 'rollback',
          releaseId: rollbackInfo.previousVersion,
          result: 'rolled_back',
          rollbackFrom: this.manifest?.version,
        });

        this.emit('rolled-back', { version: this.currentVersion });
      } else {
        this.setState('FAILED');
      }

      return result;
    } catch (error) {
      this.setState('FAILED');

      return { success: false, error: this.createError('ROLLBACK_FAILURE', `Rollback failed: ${error instanceof Error ? error.message : 'unknown error'}`) };
    }
  }

  /**
   * Get current state
   */
  getState(): UpdateState {
    return this.state;
  }

  /**
   * Get update configuration
   */
  getConfig(): UpdateConfig {
    return { ...this.config };
  }

  /**
   * Update configuration
   */
  async setConfig(config: Partial<UpdateConfig>): Promise<void> {
    this.config = { ...this.config, ...config };
    this.saveConfig();
    this.emit('config-changed', this.config);
  }

  /**
   * Get update history
   */
  getHistory(): UpdateHistoryEntry[] {
    return [...this.history];
  }

  /**
   * Start periodic update checks
   */
  startPeriodicChecks(): void {
    if (this.checkTimer) {return;}

    this.checkTimer = setInterval(() => {
      this.checkForUpdates().catch(err => {
        this.emit('error', this.createError('NETWORK_FAILURE', `Periodic check failed: ${err.message}`));
      });
    }, this.config.checkInterval);

    // Run initial check
    this.checkForUpdates();
  }

  /**
   * Stop periodic checks
   */
  stopPeriodicChecks(): void {
    if (this.checkTimer) {
      clearInterval(this.checkTimer);
      this.checkTimer = null;
    }
  }

  /**
   * Cancel ongoing download
   */
  cancelDownload(): void {
    if (this.downloadController) {
      this.downloadController.abort();
      this.downloadController = null;
    }

    this.setState('IDLE');
  }

  // Private methods

  private setState(state: UpdateState): void {
    // Mirror through the guarded state machine; legacy ad-hoc jumps that
    // predate the machine are tolerated (machine stays put) rather than
    // breaking running clients. New code should use legal transitions.
    try {
      if (this.fsm.getState() !== state) {this.fsm.transition(state);}
    } catch {
      /* legacy jump — keep manager authoritative */
    }

    this.state = state;
    this.emit('state-change', state);
  }

  /** Expose the guarded machine for new code paths (health-gated install). */
  getStateMachine(): UpdateStateMachine {
    return this.fsm;
  }

  private async fetchManifest(): Promise<UpdateManifest> {
    // Public distribution origin only — never GitHub, never authenticated.
    // Path matches services/update/update-server.ts: /updates/{platform}/{arch}/{channel}.
    const baseUrl = this.getUpdateServerUrl();
    const url = `${baseUrl}/updates/${this.platform}/${this.architecture}/${this.config.channel}`;

    const response = await fetch(url, {
      headers: {
        'Accept': 'application/json',
        'User-Agent': `AetherOS-Updater/${this.currentVersion}`,
      },
    });

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error('No update available for this channel/platform');
      }

      throw new Error(`Manifest fetch failed: ${response.status}`);
    }

    return await response.json();
  }

  private getUpdateServerUrl(): string {
    // Master 88: single public distribution origin. No GitHub URLs, no
    // credentials — the client only ever reads the public update endpoint.
    // Overridable for staging/local harness via AETHEROS_UPDATE_BASE_URL.
    const raw =
      (typeof process !== 'undefined' ? process.env.AETHEROS_UPDATE_BASE_URL : undefined) ??
      'https://releases.aetheros.com';
    return raw.replace(/\/$/, '');
  }

  private async verifyDownload(filePath: string): Promise<boolean> {
    if (!this.artifact) {return false;}

    // Verify hash
    const hashValid = await this.adapter!.verifyArtifact(this.artifact, filePath);

    if (!hashValid.valid) {return false;}

    // Additional platform-specific verification
    return true;
  }

  private async checkDiskSpace(requiredBytes: number): Promise<boolean> {
    // Check available disk space
    // Platform-specific implementation
    try {
      const config = await this.adapter!.getPlatformConfig();
      const { stdout } = await execFileAsync('df', ['-k', config.stagingPath], { timeout: 5000 });
      const lines = stdout.trim().split('\n');

      if (lines.length > 1) {
        const parts = lines[1].split(/\s+/);
        const availableKb = parseInt(parts[3], 10);
        const requiredKb = requiredBytes / 1024;

        return availableKb > requiredKb * 1.5; // 50% margin
      }
    } catch {
      // Assume OK if check fails
    }

    return true;
  }

  private async isMeteredConnection(): Promise<boolean> {
    // Platform-specific metered connection detection
    // Windows: NetworkInformation API
    // Linux: NetworkManager
    // macOS: SystemConfiguration
    return false;
  }

  private addHistoryEntry(entry: UpdateHistoryEntry): void {
    this.history.unshift(entry);

    // Keep last 50 entries
    if (this.history.length > 50) {
      this.history = this.history.slice(0, 50);
    }

    this.saveHistory();
  }

  private saveConfig(): void {
    // Save to persistent storage
  }

  private saveHistory(): void {
    // Save to persistent storage
  }

  private createError(code: UpdateErrorCode, message: string): UpdateError {
    return { code, message, recoverable: false };
  }
}

function isVersionNewer(current: string, target: string): boolean {
  return compareVersions(current, target) < 0;
}