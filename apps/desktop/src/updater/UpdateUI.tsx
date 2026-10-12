/**
 * Update UI Components
 * React components for update notifications and progress
 */

import { useStore } from '@nanostores/react';
import { AnimatePresence, motion } from 'motion/react';
import React, { useEffect, useState } from 'react';

import type { UpdateConfig, UpdateHistoryEntry } from './types';
import { $updateAvailable, $updateConfig, $updateProgress, $updateState } from './update-store';

/** Preload-exposed updater bridge (electron/preload.cjs `signedUpdater`). */
interface SignedUpdaterBridge {
  install(opts?: Record<string, unknown>): Promise<unknown>;
  setConfig(config: Partial<UpdateConfig>): Promise<unknown>;
  getHistory(): Promise<UpdateHistoryEntry[]>;
}

function signedUpdater(): SignedUpdaterBridge | undefined {
  const w = window as unknown as {
    aetherosDesktop?: { signedUpdater?: SignedUpdaterBridge };
  };

  return w.aetherosDesktop?.signedUpdater;
}

export function UpdateNotification(): React.ReactElement | null {
  const updateAvailable = useStore($updateAvailable);
  const updateState = useStore($updateState);
  const [dismissed, setDismissed] = useState(false);

  if (!updateAvailable || dismissed || updateState === 'DOWNLOADING' || updateState === 'INSTALLING') {
    return null;
  }

  return (
    <AnimatePresence>
      <motion.div
        animate={{ opacity: 1, y: 0 }}
        className="fixed bottom-4 right-4 z-50 max-w-sm"
        exit={{ opacity: 0, y: -20 }}
        initial={{ opacity: 0, y: -20 }}
      >
        <div className="bg-surface-border border border-border rounded-lg p-4 shadow-xl">
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 text-primary-500">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path d="M12 6v6m0 0v6m0-6h6m-6 0H6" strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} />
              </svg>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-text-primary">Update Available</p>
              <p className="text-sm text-text-secondary mt-1">
                A new version of AetherOS is ready to install.
              </p>
            </div>
            <div className="flex gap-2">
              <button
                className="text-sm text-text-secondary hover:text-text-primary"
                onClick={() => setDismissed(true)}
              >
                Dismiss
              </button>
              <button
                className="px-3 py-1 text-sm font-medium text-white bg-primary-500 rounded hover:bg-primary-600"
                onClick={() => void signedUpdater()?.install({})}
              >
                Install Now
              </button>
            </div>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}

export function UpdateProgressBar(): React.ReactElement | null {
  const progress = useStore($updateProgress);
  const state = useStore($updateState);

  if (!['DOWNLOADING', 'VERIFYING', 'STAGING', 'INSTALLING'].includes(state)) {
    return null;
  }

  const stateLabels: Record<string, string> = {
    DOWNLOADING: 'Downloading update',
    VERIFYING: 'Verifying download',
    STAGING: 'Preparing installation',
    INSTALLING: 'Installing update',
  };

  return (
    <AnimatePresence>
      <motion.div
        animate={{ opacity: 1, height: 'auto' }}
        className="fixed top-0 left-0 right-0 z-50 bg-surface-border border-b border-border"
        exit={{ opacity: 0, height: 0 }}
        initial={{ opacity: 0, height: 0 }}
      >
        <div className="max-w-4xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between gap-4 mb-2">
            <span className="text-sm font-medium text-text-primary">
              {stateLabels[state] || state}
            </span>
            <span className="text-sm text-text-secondary">
              {progress.percent.toFixed(1)}%
            </span>
          </div>
          <div className="h-2 bg-surface-bg rounded-full overflow-hidden">
            <motion.div
              animate={{ width: `${progress.percent}%` }}
              className="h-full bg-primary-500 rounded-full"
              initial={{ width: 0 }}
              transition={{ duration: 0.3, ease: 'easeOut' }}
            />
          </div>
          {(progress.bytesTotal && progress.bytesDownloaded) && (
            <p className="text-xs text-text-secondary mt-1 text-right">
              {formatBytes(progress.bytesDownloaded)} / {formatBytes(progress.bytesTotal)}
              {progress.speed && ` • ${formatBytes(progress.speed)}/s`}
              {progress.eta && ` • ETA: ${formatDuration(progress.eta)}`}
            </p>
          )}
        </div>
      </motion.div>
    </AnimatePresence>
  );
}

export function UpdateSettings(): React.ReactElement {
  const config = useStore($updateConfig);
  const [localConfig, setLocalConfig] = useState<UpdateConfig>(config);

  const handleChange = (key: keyof UpdateConfig, value: any) => {
    setLocalConfig(prev => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    await signedUpdater()?.setConfig(localConfig);
  };

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold text-text-primary">Update Settings</h2>

      <div className="space-y-4">
        <SettingToggle
          checked={localConfig.enabled}
          description="Automatically check for and download updates"
          label="Automatic Updates"
          onChange={checked => handleChange('enabled', checked)}
        />

        <SettingSelect
          description="Choose which release channel to follow"
          label="Update Channel"
          onChange={value => handleChange('channel', value)}
          options={[
            { value: 'stable', label: 'Stable', description: 'Stable releases only' },
            { value: 'beta', label: 'Beta', description: 'Beta releases with new features' },
            { value: 'alpha', label: 'Alpha', description: 'Early preview releases' },
            { value: 'nightly', label: 'Nightly', description: 'Latest development builds' },
          ]}
          value={localConfig.channel}
        />

        <SettingToggle
          checked={localConfig.downloadAutomatically}
          description="Download updates in the background when available"
          label="Download Automatically"
          onChange={checked => handleChange('downloadAutomatically', checked)}
        />

        <SettingToggle
          checked={localConfig.installOnQuit}
          description="Install pending updates when closing AetherOS"
          label="Install on Quit"
          onChange={checked => handleChange('installOnQuit', checked)}
        />

        <SettingToggle
          checked={localConfig.allowPrerelease}
          description="Include alpha/beta/nightly updates"
          label="Allow Pre-release"
          onChange={checked => handleChange('allowPrerelease', checked)}
        />

        <SettingSelect
          description="How to handle updates on metered connections"
          label="Metered Network Policy"
          onChange={value => handleChange('meteredNetworkPolicy', value)}
          options={[
            { value: 'allow', label: 'Allow', description: 'Download on any network' },
            { value: 'wifi-only', label: 'Wi-Fi Only', description: 'Only download on Wi-Fi' },
            { value: 'block', label: 'Block', description: 'Never download on metered networks' },
          ]}
          value={localConfig.meteredNetworkPolicy}
        />
      </div>

      <div className="flex justify-end gap-3 pt-4 border-t border-border">
        <button
          className="px-4 py-2 text-sm font-medium text-text-secondary bg-surface-bg border border-border rounded hover:bg-surface-hover"
          onClick={() => setLocalConfig(config)}
        >
          Cancel
        </button>
        <button
          className="px-4 py-2 text-sm font-medium text-white bg-primary-500 rounded hover:bg-primary-600"
          onClick={handleSave}
        >
          Save
        </button>
      </div>
    </div>
  );
}

export function UpdateHistory(): React.ReactElement {
  const [history, setHistory] = useState<UpdateHistoryEntry[]>([]);

  useEffect(() => {
    void signedUpdater()?.getHistory().then(setHistory).catch(() => setHistory([]));
  }, []);

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-text-primary">Update History</h2>

      <div className="bg-surface-border border border-border rounded-lg overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border bg-surface-bg">
              <th className="px-4 py-3 text-left text-sm font-medium text-text-secondary">Version</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-text-secondary">Date</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-text-secondary">Source</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-text-secondary">Result</th>
            </tr>
          </thead>
          <tbody>
            {history.map((entry, index) => (
              <tr className="border-b border-border hover:bg-surface-hover" key={index}>
                <td className="px-4 py-3 text-sm text-text-primary font-mono">{entry.version}</td>
                <td className="px-4 py-3 text-sm text-text-secondary">
                  {new Date(entry.installedAt).toLocaleString()}
                </td>
                <td className="px-4 py-3 text-sm text-text-secondary capitalize">{entry.source}</td>
                <td className="px-4 py-3">
                  <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                    entry.result === 'success' ? 'bg-green-500/20 text-green-400' :
                    entry.result === 'failed' ? 'bg-red-500/20 text-red-400' :
                    'bg-yellow-500/20 text-yellow-400'
                  }`}>
                    {entry.result.replace('_', ' ')}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// Helper components

function SettingToggle({
  label,
  description,
  checked,
  onChange,
}: {
  label: string;
  description: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex items-center justify-between gap-4 cursor-pointer">
      <div>
        <p className="text-sm font-medium text-text-primary">{label}</p>
        <p className="text-sm text-text-secondary">{description}</p>
      </div>
      <button
        aria-checked={checked}
        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
          checked ? 'bg-primary-500' : 'bg-surface-bg border border-border'
        }`}
        onClick={() => onChange(!checked)}
        role="switch"
      >
        <span
          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
            checked ? 'translate-x-6' : 'translate-x-0'
          }`}
        />
      </button>
    </label>
  );
}

function SettingSelect({
  label,
  description,
  value,
  options,
  onChange,
}: {
  label: string;
  description: string;
  value: string;
  options: Array<{ value: string; label: string; description: string }>;
  onChange: (value: string) => void;
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-text-primary mb-1">{label}</label>
      <p className="text-sm text-text-secondary mb-2">{description}</p>
      <select
        className="w-full px-3 py-2 text-sm text-text-primary bg-surface-bg border border-border rounded hover:border-border-focus focus:outline-none focus:ring-2 focus:ring-primary-500"
        onChange={e => onChange(e.target.value)}
        value={value}
      >
        {options.map(opt => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}

function formatBytes(bytes: number): string {
  if (bytes === 0) {return '0 B';}
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDuration(seconds: number): string {
  if (seconds < 60) {return `${Math.round(seconds)}s`;}

  if (seconds < 3600) {return `${Math.round(seconds / 60)}m`;}

  return `${Math.round(seconds / 3600)}h ${Math.round((seconds % 3600) / 60)}m`;
}