/**
 * Update State Store
 * Nanostores-based state management for update system
 */

import { atom, computed } from 'nanostores';

import type {
  ArtifactInfo,
  UpdateConfig,
  UpdateError,
  UpdateHistoryEntry,
  UpdateManifest,
  UpdateProgress,
  UpdateState,
} from './types';

const DEFAULT_CONFIG: UpdateConfig = {
  enabled: true,
  channel: 'stable',
  checkInterval: 24 * 60 * 60 * 1000,
  downloadAutomatically: true,
  installOnQuit: false,
  allowPrerelease: false,
  meteredNetworkPolicy: 'wifi-only',
  autoUpdateOnRestart: true,
  verifySignature: true,
  requireAdminForInstall: true,
};

// Core state atoms
export const $updateState = atom<UpdateState>('IDLE');
export const $updateProgress = atom<UpdateProgress>({
  state: 'IDLE',
  percent: 0,
});
export const $updateConfig = atom<UpdateConfig>(DEFAULT_CONFIG);
export const $updateManifest = atom<UpdateManifest | null>(null);
export const $updateArtifact = atom<ArtifactInfo | null>(null);
export const $updateError = atom<UpdateError | null>(null);
export const $updateHistory = atom<UpdateHistoryEntry[]>([]);
export const $updateAvailable = atom<boolean>(false);
export const $mandatoryUpdate = atom<boolean>(false);
export const $lastCheck = atom<number>(0);

// Computed values
export const $isChecking = computed($updateState, state => state === 'CHECKING');
export const $isDownloading = computed($updateState, state => state === 'DOWNLOADING');
export const $isInstalling = computed($updateState, state => state === 'INSTALLING');
export const $canInstall = computed(
  [$updateState, $updateArtifact, $updateProgress],
  (state, artifact, progress) =>
    state === 'READY_TO_INSTALL' && artifact !== null && progress.percent >= 100
);

// Actions
export function setUpdateState(state: UpdateState): void {
  $updateState.set(state);
}

export function setUpdateProgress(progress: Partial<UpdateProgress>): void {
  $updateProgress.set({ ...$updateProgress.get(), ...progress });
}

export function setUpdateConfig(config: Partial<UpdateConfig>): void {
  $updateConfig.set({ ...$updateConfig.get(), ...config });
}

export function setUpdateManifest(manifest: UpdateManifest | null): void {
  $updateManifest.set(manifest);
}

export function setUpdateArtifact(artifact: ArtifactInfo | null): void {
  $updateArtifact.set(artifact);
}

export function setUpdateError(error: UpdateError | null): void {
  $updateError.set(error);
}

export function setUpdateAvailable(available: boolean): void {
  $updateAvailable.set(available);
}

export function setMandatoryUpdate(mandatory: boolean): void {
  $mandatoryUpdate.set(mandatory);
}

export function setLastCheck(timestamp: number): void {
  $lastCheck.set(timestamp);
}

export function addHistoryEntry(entry: UpdateHistoryEntry): void {
  const history = $updateHistory.get();
  $updateHistory.set([entry, ...history.slice(0, 49)]);
}

export function loadHistory(entries: UpdateHistoryEntry[]): void {
  $updateHistory.set(entries);
}

export function loadConfig(config: UpdateConfig): void {
  $updateConfig.set(config);
}

export function resetUpdateState(): void {
  $updateState.set('IDLE');
  $updateProgress.set({ state: 'IDLE', percent: 0 });
  $updateError.set(null);
  $updateAvailable.set(false);
  $mandatoryUpdate.set(false);
  $updateArtifact.set(null);
  $updateManifest.set(null);
}