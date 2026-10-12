/**
 * Core update system types for AetherOS Universal Update Platform
 * Following the specification from MASTER PROMPT
 */

export type ReleaseChannel = 'nightly' | 'dev' | 'alpha' | 'beta' | 'stable' | 'enterprise';

export type Platform = 'win32' | 'darwin' | 'linux' | 'web' | 'ios' | 'android';

export type Architecture = 'x64' | 'arm64' | 'x86' | 'universal';

export type UpdateState =
  | 'IDLE'
  | 'CHECKING'
  | 'AVAILABLE'
  | 'DOWNLOADING'
  | 'VERIFYING'
  | 'STAGING'
  | 'READY_TO_INSTALL'
  | 'INSTALLING'
  | 'RESTARTING'
  | 'HEALTH_CHECK'
  | 'COMPLETE'
  | 'FAILED'
  | 'ROLLBACK'
  | 'ROLLED_BACK'
  | 'BLOCKED';

export type UpdateClassification = 'normal' | 'important' | 'security-critical';

export type UpdateErrorCode =
  | 'NETWORK_FAILURE'
  | 'MANIFEST_INVALID'
  | 'SIGNATURE_INVALID'
  | 'HASH_MISMATCH'
  | 'UNSUPPORTED_PLATFORM'
  | 'INSUFFICIENT_DISK'
  | 'PERMISSION_DENIED'
  | 'INSTALL_FAILURE'
  | 'MIGRATION_FAILURE'
  | 'HEALTH_CHECK_FAILURE'
  | 'CRASH_LOOP'
  | 'ROLLBACK_FAILURE'
  | 'DOWNLOAD_INTERRUPTED'
  | 'REVOKED_RELEASE'
  | 'DOWNGRADE_FORBIDDEN'
  | 'UNSUPPORTED_ARCHITECTURE'
  | 'CERTIFICATE_EXPIRED'
  | 'PROVENANCE_INVALID';

export interface SemanticVersion {
  major: number;
  minor: number;
  patch: number;
  prerelease?: string;
  build?: string;
  raw: string;
}

export interface ArtifactInfo {
  platform: Platform;
  architecture: Architecture;
  version: string;
  buildId: string;
  sourceCommit: string;
  sha256: string;
  size: number;
  signature: string;
  url: string;
  provenance: ProvenanceInfo;
  packaging: PackagingFormat;
}

export interface ProvenanceInfo {
  builder: string;
  buildTimestamp: string;
  buildWorkflow: string;
  dependencies: DependencyInfo[];
  sbomHash?: string;
}

export interface DependencyInfo {
  name: string;
  version: string;
  hash?: string;
}

export type PackagingFormat =
  | 'nsis'
  | 'msi'
  | 'dmg'
  | 'zip'
  | 'pkg'
  | 'appimage'
  | 'deb'
  | 'rpm'
  | 'flatpak'
  | 'web'
  | 'ipa'
  | 'apk'
  | 'aab';

export interface UpdateManifest {
  product: 'AetherOS';
  version: string;
  channel: ReleaseChannel;
  releaseId: string;
  commit: string;
  platforms: Record<string, ArtifactInfo>;
  minimumVersion: string;
  artifacts: ArtifactInfo[];
  releaseNotes: string;
  security: SecurityInfo;
  rollout: RolloutPolicy;
  protocolVersion: number;
  timestamp: string;
  signature: string;
}

export interface SecurityInfo {
  classification: UpdateClassification;
  cveIds?: string[];
  securityNotes?: string;
  mandatoryAfter?: string;
}

export interface RolloutPolicy {
  percentage: number;
  cohorts?: RolloutCohort[];
  startDate: string;
  endDate?: string;
  killSwitch?: boolean;
}

export interface RolloutCohort {
  id: string;
  platforms?: Platform[];
  architectures?: Architecture[];
  regions?: string[];
  channels?: ReleaseChannel[];
  percentage: number;
}

export interface UpdateConfig {
  enabled: boolean;
  channel: ReleaseChannel;
  checkInterval: number;
  downloadAutomatically: boolean;
  installOnQuit: boolean;
  allowPrerelease: boolean;
  meteredNetworkPolicy: 'allow' | 'wifi-only' | 'block';
  autoUpdateOnRestart: boolean;
  verifySignature: boolean;
  requireAdminForInstall: boolean;
}

export interface UpdateProgress {
  state: UpdateState;
  percent: number;
  bytesDownloaded?: number;
  bytesTotal?: number;
  speed?: number;
  eta?: number;
  message?: string;
  error?: UpdateError;
}

export interface UpdateError {
  code: UpdateErrorCode;
  message: string;
  recoverable: boolean;
  details?: Record<string, unknown>;
}

export interface UpdateResult {
  success: boolean;
  version?: string;
  error?: UpdateError;
  rollbackPerformed?: boolean;
}

export interface UpdateHistoryEntry {
  version: string;
  installedAt: string;
  source: 'auto' | 'manual' | 'cli' | 'rollback';
  releaseId: string;
  result: 'success' | 'failed' | 'rolled_back';
  rollbackFrom?: string;
  error?: UpdateError;
}

export interface HealthCheckResult {
  passed: boolean;
  checks: HealthCheck[];
  timestamp: string;
}

export interface HealthCheck {
  name: string;
  passed: boolean;
  message?: string;
  critical: boolean;
}

export interface MigrationInfo {
  id: string;
  version: string;
  description: string;
  precondition: (currentVersion: string) => boolean;
  execute: () => Promise<void>;
  validate: () => Promise<boolean>;
  rollback: () => Promise<void>;
}

export interface UpdateProtocol {
  protocolVersion: number;
  supportedVersions: number[];
}

export interface RollbackInfo {
  available: boolean;
  previousVersion: string;
  snapshotId?: string;
  canRollbackAppOnly: boolean;
  userDataChangedSince: boolean;
}

export interface UpdateServerResponse {
  manifest?: UpdateManifest;
  error?: UpdateError;
  revoked?: boolean;
  killSwitch?: boolean;
}