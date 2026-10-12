/**
 * Platform Update Adapter Interface
 * Abstracts platform-specific installation mechanisms
 */

import type {
  Architecture,
  ArtifactInfo,
  HealthCheckResult,
  Platform,
  RollbackInfo,
  UpdateError,
  UpdateErrorCode,
  UpdateResult} from './types';



export interface PlatformAdapter {
  readonly platform: Platform;
  readonly supportedArchitectures: Architecture[];
  readonly packagingFormats: string[];

  /**
   * Check if updates are supported on this platform
   */
  isSupported(): Promise<boolean>;

  /**
   * Get current application version and install info
   */
  getCurrentInstallInfo(): Promise<{
    version: string;
    installPath: string;
    executablePath: string;
    isPortable?: boolean;
    isPackaged?: boolean;
  }>;

  /**
   * Verify artifact before installation
   */
  verifyArtifact(artifact: ArtifactInfo, localPath: string): Promise<{
    valid: boolean;
    error?: UpdateError;
  }>;

  /**
   * Stage the update (download to staging area, prepare for install)
   */
  stageUpdate(artifact: ArtifactInfo, localPath: string): Promise<{
    success: boolean;
    stagedPath?: string;
    error?: UpdateError;
  }>;

  /**
   * Install the staged update
   */
  installUpdate(stagedPath: string, options: InstallOptions): Promise<UpdateResult>;

  /**
   * Perform rollback to previous version
   */
  rollback(rollbackInfo: RollbackInfo): Promise<UpdateResult>;

  /**
   * Run health checks after update
   */
  runHealthChecks(version: string): Promise<HealthCheckResult>;

  /**
   * Get rollback information
   */
  getRollbackInfo(): Promise<RollbackInfo>;

  /**
   * Clean up temporary files after successful update
   */
  cleanup(stagedPath: string): Promise<void>;

  /**
   * Check if running with admin/root privileges (required for install)
   */
  hasInstallPermissions(): Promise<boolean>;

  /**
   * Request elevation if needed
   */
  requestElevation(): Promise<boolean>;

  /**
   * Get platform-specific update configuration
   */
  getPlatformConfig(): PlatformUpdateConfig;
}

export interface InstallOptions {
  restartAfterInstall: boolean;
  runHealthChecks: boolean;
  createBackup: boolean;
  silent: boolean;
}

export interface PlatformUpdateConfig {
  installPath: string;
  stagingPath: string;
  backupPath: string;
  requiresElevation: boolean;
  supportsRollback: boolean;
  supportsDeltaUpdates: boolean;
  maxArtifactSize: number;
  tempDirectory: string;
}

/**
 * Base class for platform adapters with common functionality
 */
export abstract class BasePlatformAdapter implements PlatformAdapter {
  abstract readonly platform: Platform;
  abstract readonly supportedArchitectures: Architecture[];
  abstract readonly packagingFormats: string[];

  abstract isSupported(): Promise<boolean>;
  abstract getCurrentInstallInfo(): Promise<{
    version: string;
    installPath: string;
    executablePath: string;
    isPortable?: boolean;
    isPackaged?: boolean;
  }>;

  abstract verifyArtifact(artifact: ArtifactInfo, localPath: string): Promise<{
    valid: boolean;
    error?: UpdateError;
  }>;

  abstract stageUpdate(artifact: ArtifactInfo, localPath: string): Promise<{
    success: boolean;
    stagedPath?: string;
    error?: UpdateError;
  }>;

  abstract installUpdate(stagedPath: string, options: InstallOptions): Promise<UpdateResult>;

  abstract rollback(rollbackInfo: RollbackInfo): Promise<UpdateResult>;

  abstract runHealthChecks(version: string): Promise<HealthCheckResult>;

  abstract getRollbackInfo(): Promise<RollbackInfo>;

  abstract cleanup(stagedPath: string): Promise<void>;

  abstract hasInstallPermissions(): Promise<boolean>;

  abstract requestElevation(): Promise<boolean>;

  abstract getPlatformConfig(): PlatformUpdateConfig;

  /**
   * Common hash verification
   */
  protected async verifyHash(filePath: string, expectedSha256: string): Promise<boolean> {
    // Implementation in platform-specific subclasses
    throw new Error('verifyHash must be implemented by platform adapter');
  }

  /**
   * Common signature verification
   */
  protected async verifySignature(filePath: string, signature: string): Promise<boolean> {
    // Implementation in platform-specific subclasses
    throw new Error('verifySignature must be implemented by platform adapter');
  }

  /**
   * Create a standard error response
   */
  protected createError(code: UpdateErrorCode, message: string, recoverable = false, details?: Record<string, unknown>): UpdateError {
    return { code, message, recoverable, details };
  }
}

/**
 * Platform adapter factory
 */
export class PlatformAdapterFactory {
  private static adapters: Map<Platform, PlatformAdapter> = new Map();

  static register(adapter: PlatformAdapter): void {
    this.adapters.set(adapter.platform, adapter);
  }

  static get(platform: Platform): PlatformAdapter | undefined {
    return this.adapters.get(platform);
  }

  static async getForCurrentPlatform(): Promise<PlatformAdapter> {
    const platform = (await import('node:process')).platform;
    const adapter = this.get(platform as Platform);

    if (!adapter) {
      throw new Error(`No platform adapter registered for ${platform}`);
    }

    if (!(await adapter.isSupported())) {
      throw new Error(`Platform ${platform} is not supported for updates`);
    }

    return adapter;
  }

  static getAll(): PlatformAdapter[] {
    return Array.from(this.adapters.values());
  }
}

/**
 * Update installation coordinator using platform adapters
 */
export class UpdateInstaller {
  private adapter: PlatformAdapter;

  constructor(adapter: PlatformAdapter) {
    this.adapter = adapter;
  }

  async install(
    artifact: ArtifactInfo,
    localPath: string,
    options: InstallOptions
  ): Promise<UpdateResult> {
    // 1. Verify artifact
    const verification = await this.adapter.verifyArtifact(artifact, localPath);

    if (!verification.valid) {
      return { success: false, error: verification.error };
    }

    // 2. Stage update
    const staging = await this.adapter.stageUpdate(artifact, localPath);

    if (!staging.success) {
      return { success: false, error: staging.error };
    }

    // 3. Check permissions
    if (await this.adapter.hasInstallPermissions() === false) {
      const elevated = await this.adapter.requestElevation();

      if (!elevated) {
        return {
          success: false,
          error: this.createError('PERMISSION_DENIED', 'Installation requires elevated privileges'),
        };
      }
    }

    // 4. Install
    const result = await this.adapter.installUpdate(staging.stagedPath!, options);

    // 5. Cleanup on success
    if (result.success && staging.stagedPath) {
      await this.adapter.cleanup(staging.stagedPath);
    }

    return result;
  }

  private createError(code: UpdateErrorCode, message: string): UpdateError {
    return { code, message, recoverable: false };
  }
}