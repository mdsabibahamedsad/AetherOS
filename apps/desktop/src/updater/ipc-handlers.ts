/**
 * Update IPC Handlers
 * Main process handlers for update system communication
 */

import type * as nodeFs from 'node:fs';
import type * as nodeFsPromises from 'node:fs/promises';
import type * as nodePath from 'node:path';

import { app, ipcMain } from 'electron';

import type { UpdateConfig, UpdateHistoryEntry, UpdateProgress, UpdateState } from './types';
import { UpdateManager } from './update-manager';

let updateManager: UpdateManager | null = null;
let isInitialized = false;

export function initializeUpdateIPC(): void {
  if (isInitialized) {return;}

  // Initialize update manager
  initializeUpdateManager();

  // Register IPC handlers
  registerHandlers();

  isInitialized = true;
}

async function initializeUpdateManager(): Promise<void> {
  const version = app.getVersion();
  const platform = process.platform as any;
  const architecture = process.arch === 'arm64' ? 'arm64' : 'x64';

  updateManager = new UpdateManager(version, {}, platform, architecture);

  try {
    await updateManager.initialize();

    // Set up event listeners
    updateManager.on('state-change', (state: UpdateState) => {
      broadcastToRenderers('update:state-change', state);
    });

    updateManager.on('download-progress', (progress: UpdateProgress) => {
      broadcastToRenderers('update:progress', progress);
    });

    updateManager.on('update-available', (info: any) => {
      broadcastToRenderers('update:available', info);
    });

    updateManager.on('installed', (info: any) => {
      broadcastToRenderers('update:installed', info);
    });

    updateManager.on('rolled-back', (info: any) => {
      broadcastToRenderers('update:rolled-back', info);
    });

    updateManager.on('error', (error: any) => {
      broadcastToRenderers('update:error', error);
    });

    // Load saved config
    await loadConfig();

    // Start periodic checks if enabled
    const config = updateManager.getConfig();

    if (config.enabled) {
      updateManager.startPeriodicChecks();
    }
  } catch (error) {
    console.error('[Update] Failed to initialize:', error);
  }
}

function registerHandlers(): void {
  // Get current state
  ipcMain.handle('update:get-state', () => {
    return updateManager?.getState() || 'IDLE';
  });

  // Get config
  ipcMain.handle('update:get-config', () => {
    return updateManager?.getConfig() || {};
  });

  // Set config
  ipcMain.handle('update:set-config', async (_, config: Partial<UpdateConfig>) => {
    if (updateManager) {
      await updateManager.setConfig(config);
    }

    return { success: true };
  });

  // Check for updates
  ipcMain.handle('update:check', async (_, force = false) => {
    if (!updateManager) {
      return { updateAvailable: false, error: 'Update manager not initialized' };
    }

    if (force !== true && force !== false) {
      return { updateAvailable: false, error: 'Invalid force flag' };
    }

    return await updateManager.checkForUpdates(force);
  });

  // Download update
  ipcMain.handle('update:download', async () => {
    if (!updateManager) {
      return { success: false, error: 'Update manager not initialized' };
    }

    return await updateManager.downloadUpdate();
  });

  // Install update — renderer may REQUEST, main validates + executes.
  // Only boolean flags are accepted; everything else is ignored.
  ipcMain.handle('update:install', async (_, options: unknown = {}) => {
    if (!updateManager) {
      return { success: false, error: 'Update manager not initialized' };
    }

    const o = (options ?? {}) as Record<string, unknown>;

    const clean = {
      restartAfterInstall: o.restartAfterInstall === true,
      runHealthChecks: o.runHealthChecks !== false,
      createBackup: o.createBackup !== false,
      silent: o.silent === true,
    };

    return await updateManager.installUpdate(clean);
  });

  // Rollback
  ipcMain.handle('update:rollback', async () => {
    if (!updateManager) {
      return { success: false, error: 'Update manager not initialized' };
    }

    return await updateManager.rollback();
  });

  // Get history
  ipcMain.handle('update:get-history', async () => {
    // Load from persistent storage
    return loadHistory();
  });

  // Get rollback info
  ipcMain.handle('update:get-rollback-info', async () => {
    if (!updateManager) {
      return { available: false, previousVersion: 'unknown' };
    }

    // This would use the platform adapter
    return { available: false, previousVersion: 'unknown' };
  });

  // Open update settings
  ipcMain.handle('update:open-settings', async () => {
    // Open settings window to update tab
    return { success: true };
  });

  // Cancel download
  ipcMain.handle('update:cancel-download', async () => {
    if (updateManager) {
      updateManager.cancelDownload();
    }

    return { success: true };
  });

  // Manual restart after update
  ipcMain.handle('update:restart', async () => {
    app.relaunch();
    app.exit(0);
  });
}

function broadcastToRenderers(channel: string, data: any): void {
  const { BrowserWindow } = require('electron');

  for (const window of BrowserWindow.getAllWindows()) {
    if (!window.isDestroyed()) {
      window.webContents.send(channel, data);
    }
  }
}

async function loadConfig(): Promise<void> {
  // Load config from storage
  try {
     
    const fs = require('node:fs/promises') as typeof nodeFsPromises;
     
    const path = require('node:path') as typeof nodePath;
    const configPath = path.join(app.getPath('userData'), 'update-config.json');
    const data = await fs.readFile(configPath, 'utf-8');
    const config = JSON.parse(data);

    if (updateManager) {
      await updateManager.setConfig(config);
    }
  } catch {
    // No config saved yet
  }
}

async function saveConfig(config: UpdateConfig): Promise<void> {
  try {
     
    const fs = require('node:fs/promises') as typeof nodeFsPromises;
     
    const path = require('node:path') as typeof nodePath;
    const configPath = path.join(app.getPath('userData'), 'update-config.json');
    await fs.writeFile(configPath, JSON.stringify(config, null, 2));
  } catch (error) {
    console.error('[Update] Failed to save config:', error);
  }
}

function loadHistory(): UpdateHistoryEntry[] {
  try {
     
    const fs = require('node:fs') as typeof nodeFs;
     
    const path = require('node:path') as typeof nodePath;
    const historyPath = path.join(app.getPath('userData'), 'update-history.json');

    return JSON.parse(fs.readFileSync(historyPath, 'utf-8'));
  } catch {
    return [];
  }
}

function saveHistory(history: UpdateHistoryEntry[]): void {
  try {
     
    const fs = require('node:fs') as typeof nodeFs;
     
    const path = require('node:path') as typeof nodePath;
    const historyPath = path.join(app.getPath('userData'), 'update-history.json');
    fs.writeFileSync(historyPath, JSON.stringify(history, null, 2));
  } catch (error) {
    console.error('[Update] Failed to save history:', error);
  }
}

// Export for use in main.cjs
export { updateManager };