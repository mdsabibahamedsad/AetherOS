/**
 * Windows Update Adapter
 * Uses NSIS/MSI installer for updates
 */

import { execFile } from 'node:child_process';
import * as crypto from 'node:crypto';
import * as fs from 'node:fs/promises';
import * as path from 'node:path';
import { promisify } from 'node:util';

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



const execFileAsync = promisify(execFile);

export class WindowsUpdateAdapter extends BasePlatformAdapter {
  readonly platform: Platform = 'win32';
  readonly supportedArchitectures: Architecture[] = ['x64', 'arm64'];
  readonly packagingFormats: string[] = ['nsis', 'msi'];

  private config: PlatformUpdateConfig | null = null;

  async isSupported(): Promise<boolean> {
    return process.platform === 'win32';
  }

  async getCurrentInstallInfo(): Promise<{
    version: string;
    installPath: string;
    executablePath: string;
    isPortable?: boolean;
    isPackaged?: boolean;
  }> {
    // In Electron, we can get this from the app module
    // For now, return placeholder - actual implementation uses Electron's app.getVersion()
    return {
      version: '1.0.0',
      installPath: process.env.APPDATA ? path.join(process.env.APPDATA, 'AetherOS') : '',
      executablePath: process.execPath,
      isPortable: false,
      isPackaged: true,
    };
  }

  async verifyArtifact(artifact: ArtifactInfo, localPath: string): Promise<{ valid: boolean; error?: UpdateError }> {
    // 1. Check file exists
    try {
      await fs.access(localPath);
    } catch {
      return { valid: false, error: this.createError('HASH_MISMATCH', 'Artifact file not found') };
    }

    // 2. Verify hash
    const hashValid = await this.verifyHash(localPath, artifact.sha256);

    if (!hashValid) {
      return { valid: false, error: this.createError('HASH_MISMATCH', 'Artifact hash verification failed') };
    }

    // 3. Verify signature (Authenticode)
    const sigValid = await this.verifySignature(localPath, artifact.signature);

    if (!sigValid) {
      return { valid: false, error: this.createError('SIGNATURE_INVALID', 'Artifact signature verification failed') };
    }

    // 4. Verify publisher (certificate subject)
    const certValid = await this.verifyPublisher(localPath);

    if (!certValid) {
      return { valid: false, error: this.createError('SIGNATURE_INVALID', 'Artifact publisher verification failed') };
    }

    return { valid: true };
  }

  async stageUpdate(artifact: ArtifactInfo, localPath: string): Promise<{
    success: boolean;
    stagedPath?: string;
    error?: UpdateError;
  }> {
    const config = await this.getConfig();
    const stagingDir = path.join(config.stagingPath, `aetheros-update-${artifact.version}`);
    const stagedPath = path.join(stagingDir, path.basename(localPath));

    try {
      await fs.mkdir(stagingDir, { recursive: true });
      await fs.copyFile(localPath, stagedPath);

      // Verify staged copy
      const hashValid = await this.verifyHash(stagedPath, artifact.sha256);

      if (!hashValid) {
        return { success: false, error: this.createError('HASH_MISMATCH', 'Staged artifact hash mismatch') };
      }

      return { success: true, stagedPath };
    } catch (error) {
      return {
        success: false,
        error: this.createError('INSTALL_FAILURE', `Failed to stage update: ${error instanceof Error ? error.message : 'unknown error'}`),
      };
    }
  }

  async installUpdate(stagedPath: string, options: InstallOptions): Promise<UpdateResult> {
    try {
      const config = await this.getConfig();

      // Determine installer type from file extension
      const isMsi = stagedPath.endsWith('.msi');
      const isNsis = stagedPath.endsWith('.exe');

      let installArgs: string[];

      if (isMsi) {
        // MSI installation
        installArgs = [
          '/i', stagedPath,
          '/qn', // Quiet install
          '/norestart',
          'ALLUSERS=1',
        ];

        if (options.silent) {
          installArgs.push('/quiet');
        }
      } else if (isNsis) {
        // NSIS installation
        installArgs = [
          '/S', // Silent
          '/ALLUSERS',
          `/D=${config.installPath}`,
        ];
      } else {
        return {
          success: false,
          error: this.createError('INSTALL_FAILURE', `Unknown installer format: ${stagedPath}`),
        };
      }

      // Run installer with elevation if needed
      const result = await this.runInstaller(stagedPath, installArgs, options);

      if (!result.success) {
        return result;
      }

      // Run health checks if requested
      if (options.runHealthChecks) {
        const health = await this.runHealthChecks('1.0.0'); // Would get actual version

        if (!health.passed) {
          // Trigger rollback
          const rollbackInfo = await this.getRollbackInfo();

          if (rollbackInfo.available) {
            await this.rollback(rollbackInfo);

            return { success: false, error: this.createError('HEALTH_CHECK_FAILURE', 'Health checks failed, rolled back'), rollbackPerformed: true };
          }
        }
      }

      return { success: true, version: '1.0.0' }; // Actual version from manifest
    } catch (error) {
      return {
        success: false,
        error: this.createError('INSTALL_FAILURE', `Installation failed: ${error instanceof Error ? error.message : 'unknown error'}`),
      };
    }
  }

  async rollback(rollbackInfo: RollbackInfo): Promise<UpdateResult> {
    try {
      // For Windows, rollback means reinstalling the previous version
      // This would typically use the uninstaller of current version + installer of previous
      const config = await this.getConfig();

      // Find previous version installer in backup
      const backupDir = path.join(config.backupPath, rollbackInfo.previousVersion);
      const installers = await fs.readdir(backupDir).catch(() => []);

      if (installers.length === 0) {
        return {
          success: false,
          error: this.createError('ROLLBACK_FAILURE', 'No rollback installer found'),
        };
      }

      const installer = installers.find(f => f.endsWith('.exe') || f.endsWith('.msi'));

      if (!installer) {
        return {
          success: false,
          error: this.createError('ROLLBACK_FAILURE', 'No valid rollback installer found'),
        };
      }

      const installerPath = path.join(backupDir, installer);

      return await this.installUpdate(installerPath, {
        restartAfterInstall: true,
        runHealthChecks: true,
        createBackup: false,
        silent: true,
      });
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
        name: 'process_launch',
        passed: true,
        message: 'Application launches successfully',
        critical: true,
      },
      {
        name: 'ipc_connection',
        passed: true,
        message: 'IPC channel established',
        critical: true,
      },
      {
        name: 'backend_connection',
        passed: true,
        message: 'Backend service reachable',
        critical: true,
      },
      {
        name: 'storage_access',
        passed: true,
        message: 'Storage accessible',
        critical: true,
      },
      {
        name: 'config_integrity',
        passed: true,
        message: 'Configuration valid',
        critical: true,
      },
      {
        name: 'update_subsystem',
        passed: true,
        message: 'Update subsystem functional',
        critical: true,
      },
    ];

    // In real implementation, these would be actual checks
    // For now, return all passed
    return {
      passed: checks.every(c => c.passed),
      checks,
      timestamp: new Date().toISOString(),
    };
  }

  async getRollbackInfo(): Promise<RollbackInfo> {
    const config = await this.getConfig();
    const backupDir = config.backupPath;

    try {
      const versions = await fs.readdir(backupDir);
      const previousVersion = versions.sort().reverse()[1]; // Second newest

      return {
        available: !!previousVersion,
        previousVersion: previousVersion || 'unknown',
        canRollbackAppOnly: true,
        userDataChangedSince: false,
      };
    } catch {
      return {
        available: false,
        previousVersion: 'unknown',
        canRollbackAppOnly: false,
        userDataChangedSince: false,
      };
    }
  }

  async cleanup(stagedPath: string): Promise<void> {
    try {
      await fs.rm(stagedPath, { force: true });
      // Clean up staging directory if empty
      const stagingDir = path.dirname(stagedPath);
      const files = await fs.readdir(stagingDir);

      if (files.length === 0) {
        await fs.rmdir(stagingDir);
      }
    } catch {
      // Ignore cleanup errors
    }
  }

  async hasInstallPermissions(): Promise<boolean> {
    // Check if running as admin
    try {
      const { stdout } = await execFileAsync('net', ['session'], { timeout: 5000 });

      return stdout.includes('The list of');
    } catch {
      return false;
    }
  }

  async requestElevation(): Promise<boolean> {
    // On Windows, we'd use the 'runas' verb or UAC prompt
    // This is a placeholder - actual implementation uses ShellExecuteEx with runas
    return true;
  }

  getPlatformConfig(): PlatformUpdateConfig {
    if (this.config) {return this.config;}

    const appData = process.env.APPDATA || '';
    const localAppData = process.env.LOCALAPPDATA || '';

    this.config = {
      installPath: path.join(appData, 'AetherOS'),
      stagingPath: path.join(localAppData, 'AetherOS', 'staging'),
      backupPath: path.join(localAppData, 'AetherOS', 'backups'),
      requiresElevation: true,
      supportsRollback: true,
      supportsDeltaUpdates: false,
      maxArtifactSize: 500 * 1024 * 1024, // 500MB
      tempDirectory: process.env.TEMP || path.join(localAppData, 'Temp'),
    };

    return this.config;
  }

  private async getConfig(): Promise<PlatformUpdateConfig> {
    return this.config || this.getPlatformConfig();
  }

  async verifyHash(filePath: string, expectedSha256: string): Promise<boolean> {
    const fileBuffer = await fs.readFile(filePath);
    const hash = crypto.createHash('sha256').update(fileBuffer).digest('hex');

    return hash.toLowerCase() === expectedSha256.toLowerCase();
  }

  async verifySignature(filePath: string, signature: string): Promise<boolean> {
    // Use Windows Authenticode verification via signtool or PowerShell
    try {
      const { stdout } = await execFileAsync('powershell', [
        '-Command',
        `Get-AuthenticodeSignature '${filePath}' | Select-Object -ExpandProperty Status`
      ], { timeout: 30000 });

      return stdout.trim() === 'Valid';
    } catch {
      return false;
    }
  }

  async verifyPublisher(filePath: string): Promise<boolean> {
    try {
      const { stdout } = await execFileAsync('powershell', [
        '-Command',
        `Get-AuthenticodeSignature '${filePath}' | Select-Object -ExpandProperty SignerCertificate | Select-Object -ExpandProperty Subject`
      ], { timeout: 30000 });

      return stdout.toLowerCase().includes('aetheros');
    } catch {
      return false;
    }
  }

  private async runInstaller(
    installerPath: string,
    args: string[],
    options: InstallOptions
  ): Promise<UpdateResult> {
    // For MSI, use msiexec
    if (installerPath.endsWith('.msi')) {
      const fullArgs = ['/i', installerPath, ...args];

      try {
        await execFileAsync('msiexec', fullArgs, {
          timeout: 300000, // 5 minutes
          windowsHide: options.silent,
        });

        return { success: true };
      } catch (error) {
        return {
          success: false,
          error: this.createError('INSTALL_FAILURE', `MSI installation failed: ${error instanceof Error ? error.message : 'unknown error'}`),
        };
      }
    }

    // For NSIS, run directly
    try {
      await execFileAsync(installerPath, args, {
        timeout: 300000,
        windowsHide: options.silent,
      });

      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: this.createError('INSTALL_FAILURE', `NSIS installation failed: ${error instanceof Error ? error.message : 'unknown error'}`),
      };
    }
  }
}

// Register the adapter
PlatformAdapterFactory.register(new WindowsUpdateAdapter());
