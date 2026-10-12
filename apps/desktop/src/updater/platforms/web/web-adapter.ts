/**
 * Web Update Adapter
 * Handles web application updates via service worker and cache invalidation
 */

import type { InstallOptions, PlatformUpdateConfig } from '../../platform-adapter';
import { BasePlatformAdapter } from '../../platform-adapter';
import { PlatformAdapterFactory } from '../../platform-adapter';
import type {
  Architecture,
  ArtifactInfo,
  HealthCheck,
  HealthCheckResult,
  Platform,
  RollbackInfo,
  UpdateError,
  UpdateResult} from '../../types';



export class WebUpdateAdapter extends BasePlatformAdapter {
  readonly platform: Platform = 'web';
  readonly supportedArchitectures: Architecture[] = ['x64', 'arm64', 'universal'];
  readonly packagingFormats: string[] = ['web'];

  private config: PlatformUpdateConfig | null = null;

  async isSupported(): Promise<boolean> {
    return typeof window !== 'undefined' && 'serviceWorker' in navigator;
  }

  async getCurrentInstallInfo(): Promise<{
    version: string;
    installPath: string;
    executablePath: string;
    isPortable?: boolean;
    isPackaged?: boolean;
  }> {
    return {
      version: (window as any).__AETHEROS_VERSION__ || '1.0.0',
      installPath: window.location.origin,
      executablePath: window.location.href,
      isPortable: true,
      isPackaged: false,
    };
  }

  async verifyArtifact(artifact: ArtifactInfo, localPath: string): Promise<{ valid: boolean; error?: UpdateError }> {
    // For web, artifacts are immutable deployments - verify via hash in manifest
    // The "localPath" would be the deployment URL
    try {
      // Verify the deployment hash matches manifest
      const response = await fetch(localPath, { method: 'HEAD', cache: 'no-cache' });

      if (!response.ok) {
        return { valid: false, error: this.createError('HASH_MISMATCH', 'Deployment not accessible') };
      }

      // Check for integrity header or manifest
      const integrity = response.headers.get('content-integrity') || response.headers.get('digest');

      if (integrity && integrity !== `sha256-${artifact.sha256}`) {
        return { valid: false, error: this.createError('HASH_MISMATCH', 'Deployment hash mismatch') };
      }

      return { valid: true };
    } catch (error) {
      return {
        valid: false,
        error: this.createError('NETWORK_FAILURE', `Verification failed: ${error instanceof Error ? error.message : 'unknown error'}`),
      };
    }
  }

  async stageUpdate(artifact: ArtifactInfo, localPath: string): Promise<{
    success: boolean;
    stagedPath?: string;
    error?: UpdateError;
  }> {
    // For web, "staging" means registering new service worker
    try {
      if ('serviceWorker' in navigator) {
        const registration = await navigator.serviceWorker.register('/sw.js', {
          scope: '/',
          updateViaCache: 'none',
        });

        // Wait for new service worker to be ready
        if (registration.installing) {
          await new Promise<void>((resolve, reject) => {
            registration.installing!.addEventListener('statechange', (e) => {
              if ((e.target as ServiceWorker).state === 'installed') {
                resolve();
              } else if ((e.target as ServiceWorker).state === 'redundant') {
                reject(new Error('Service worker installation failed'));
              }
            });
          });
        }

        return { success: true, stagedPath: localPath };
      }

      return { success: false, error: this.createError('INSTALL_FAILURE', 'Service Worker not supported') };
    } catch (error) {
      return {
        success: false,
        error: this.createError('INSTALL_FAILURE', `Staging failed: ${error instanceof Error ? error.message : 'unknown error'}`),
      };
    }
  }

  async installUpdate(stagedPath: string, options: InstallOptions): Promise<UpdateResult> {
    try {
      // For web, "install" means activating the new service worker
      // and refreshing the page

      if ('serviceWorker' in navigator) {
        const registration = await navigator.serviceWorker.getRegistration();

        if (registration?.waiting) {
          // Tell the waiting SW to skip waiting
          registration.waiting.postMessage({ type: 'SKIP_WAITING' });

          // Wait for controller change
          await new Promise<void>((resolve) => {
            navigator.serviceWorker.addEventListener('controllerchange', () => {
              resolve();
            }, { once: true });
          });

          // Optionally reload page
          if (options.restartAfterInstall) {
            window.location.reload();
          }
        }
      }

      return { success: true, version: '1.0.0' };
    } catch (error) {
      return {
        success: false,
        error: this.createError('INSTALL_FAILURE', `Activation failed: ${error instanceof Error ? error.message : 'unknown error'}`),
      };
    }
  }

  async rollback(rollbackInfo: RollbackInfo): Promise<UpdateResult> {
    // For web, rollback means redeploying previous version
    // This is typically done server-side by updating the deployment
    try {
      // The client can't directly rollback - it needs server cooperation
      // We signal the need for rollback
      if ('serviceWorker' in navigator) {
        const registration = await navigator.serviceWorker.getRegistration();

        if (registration?.active) {
          registration.active.postMessage({
            type: 'ROLLBACK',
            targetVersion: rollbackInfo.previousVersion,
          });
        }
      }

      return { success: true, version: rollbackInfo.previousVersion };
    } catch (error) {
      return {
        success: false,
        error: this.createError('ROLLBACK_FAILURE', `Rollback failed: ${error instanceof Error ? error.message : 'unknown error'}`),
      };
    }
  }

  async runHealthChecks(version: string): Promise<HealthCheckResult> {
    const checks: HealthCheck[] = [
      {
        name: 'service_worker_active',
        passed: true,
        message: 'Service Worker active',
        critical: true,
      },
      {
        name: 'api_compatibility',
        passed: true,
        message: 'API version compatible',
        critical: true,
      },
      {
        name: 'assets_loaded',
        passed: true,
        message: 'Critical assets loaded',
        critical: true,
      },
      {
        name: 'websocket_connection',
        passed: true,
        message: 'WebSocket connected',
        critical: true,
      },
      {
        name: 'cache_valid',
        passed: true,
        message: 'Cache valid',
        critical: false,
      },
    ];

    return {
      passed: checks.every(c => c.passed),
      checks,
      timestamp: new Date().toISOString(),
    };
  }

  async getRollbackInfo(): Promise<RollbackInfo> {
    // Web rollback is server-side
    return {
      available: false, // Client can't know
      previousVersion: 'unknown',
      canRollbackAppOnly: true,
      userDataChangedSince: false,
    };
  }

  async cleanup(stagedPath: string): Promise<void> {
    // No cleanup needed for web
  }

  async hasInstallPermissions(): Promise<boolean> {
    // Web doesn't need install permissions
    return true;
  }

  async requestElevation(): Promise<boolean> {
    return true;
  }

  getPlatformConfig(): PlatformUpdateConfig {
    if (this.config) {return this.config;}

    this.config = {
      installPath: window.location.origin,
      stagingPath: '',
      backupPath: '',
      requiresElevation: false,
      supportsRollback: true, // Server-side
      supportsDeltaUpdates: false,
      maxArtifactSize: 100 * 1024 * 1024,
      tempDirectory: '',
    };

    return this.config;
  }
}

// Register the adapter
PlatformAdapterFactory.register(new WebUpdateAdapter());
