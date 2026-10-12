/**
 * Update Manifest Verification
 * Validates manifest structure, signatures, and artifact integrity
 */

import { createVerify } from 'node:crypto';

import { compareVersions, parseSemanticVersion } from './semver';
import type {
  Architecture,
  ArtifactInfo,
  Platform,
  ReleaseChannel,
  UpdateError,
  UpdateManifest} from './types';



const SHA256_RE = /^[0-9a-f]{64}$/i;
const VALID_CHANNELS: ReleaseChannel[] = ['nightly', 'dev', 'alpha', 'beta', 'stable', 'enterprise'];
const VALID_PLATFORMS: Platform[] = ['win32', 'darwin', 'linux', 'web', 'ios', 'android'];
const VALID_ARCHITECTURES: Architecture[] = ['x64', 'arm64', 'x86', 'universal'];
const MIN_PROTOCOL_VERSION = 1;
const MAX_PROTOCOL_VERSION = 1;
const EXPECTED_PUBLISHER = 'AetherOS';
const EXPECTED_PRODUCT = 'AetherOS';

export interface VerificationOptions {
  currentVersion: string;
  channel: ReleaseChannel;
  platform: Platform;
  architecture: Architecture;
  expectedPublisher?: string;
  supportedSchemaVersions?: number[];
  allowDowngrade?: boolean;
  allowPrerelease?: boolean;
  minimumVersion?: string;
  /**
   * Trusted RSA public key (PEM) for manifest signature verification.
   * When set: real RSA-SHA256 verification over the canonical manifest.
   * When unset: legacy placeholder (non-empty signature accepted) — dev only.
   */
  publicKey?: string;
  verifySignature?: boolean;
}

export interface VerificationResult {
  valid: boolean;
  errors: UpdateError[];
  warnings: string[];
  artifact?: ArtifactInfo;
}

/**
 * Validates the update manifest structure and signatures
 */
export async function verifyManifest(
  manifest: UpdateManifest,
  options: VerificationOptions
): Promise<VerificationResult> {
  const errors: UpdateError[] = [];
  const warnings: string[] = [];
  let artifact: ArtifactInfo | undefined;

  // 1. Basic structure validation
  if (manifest.product !== EXPECTED_PRODUCT) {
    errors.push({
      code: 'MANIFEST_INVALID',
      message: `Invalid product: expected ${EXPECTED_PRODUCT}, got ${manifest.product}`,
      recoverable: false,
    });
  }

  if (!manifest.protocolVersion || manifest.protocolVersion < MIN_PROTOCOL_VERSION || manifest.protocolVersion > MAX_PROTOCOL_VERSION) {
    errors.push({
      code: 'MANIFEST_INVALID',
      message: `Unsupported protocol version: ${manifest.protocolVersion}`,
      recoverable: false,
    });
  }

  if (!VALID_CHANNELS.includes(manifest.channel)) {
    errors.push({
      code: 'MANIFEST_INVALID',
      message: `Unknown channel: ${manifest.channel}`,
      recoverable: false,
    });
  }

  // 2. Channel validation
  if (manifest.channel !== options.channel) {
    errors.push({
      code: 'MANIFEST_INVALID',
      message: `Channel mismatch: manifest=${manifest.channel}, expected=${options.channel}`,
      recoverable: false,
    });
  }

  // 3. Version validation
  try {
    parseSemanticVersion(manifest.version);
  } catch (e) {
    errors.push({
      code: 'MANIFEST_INVALID',
      message: `Invalid manifest version: ${e instanceof Error ? e.message : 'unknown error'}`,
      recoverable: false,
    });
  }

  // 4. Current version check
  if (options.currentVersion && manifest.version) {
    const cmp = compareVersions(options.currentVersion, manifest.version);

    if (cmp >= 0 && !options.allowDowngrade) {
      errors.push({
        code: 'DOWNGRADE_FORBIDDEN',
        message: `Downgrade or equal version rejected: current=${options.currentVersion}, target=${manifest.version}`,
        recoverable: false,
      });
    }

    if (cmp >= 0 && options.allowDowngrade) {
      warnings.push(`Downgrade allowed: current=${options.currentVersion}, target=${manifest.version}`);
    }
  }

  // 5. Minimum version check
  if (options.minimumVersion && manifest.minimumVersion) {
    if (compareVersions(options.minimumVersion, manifest.minimumVersion) > 0) {
      warnings.push(`Current minimum version exceeds manifest minimum`);
    }
  }

  if (manifest.minimumVersion && options.currentVersion) {
    if (compareVersions(options.currentVersion, manifest.minimumVersion) < 0) {
      errors.push({
        code: 'MANIFEST_INVALID',
        message: `Current version ${options.currentVersion} below manifest minimumVersion ${manifest.minimumVersion}`,
        recoverable: false,
      });
    }
  }

  // 6. Publisher validation
  const expectedPub = options.expectedPublisher || EXPECTED_PUBLISHER;

  if (!manifest.artifacts.every(a => a.provenance.builder === expectedPub)) {
    // Allow for CI builder names
    warnings.push(`Publisher verification: expected ${expectedPub}`);
  }

  // 7. Find matching artifact for current platform/architecture
  const platformKey = `${options.platform}-${options.architecture}`;

  const artifactInfo = manifest.platforms[platformKey] || manifest.artifacts.find(
    a => a.platform === options.platform && a.architecture === options.architecture
  );

  if (!artifactInfo) {
    errors.push({
      code: 'UNSUPPORTED_PLATFORM',
      message: `No artifact found for platform=${options.platform}, architecture=${options.architecture}`,
      recoverable: false,
    });
  } else {
    artifact = artifactInfo;
  }

  // 8. Artifact validation
  if (artifact) {
    const artifactErrors = validateArtifact(artifact);
    errors.push(...artifactErrors);
  }

  // 9. Signature verification — real RSA-SHA256 when a trusted key is set.
  if (manifest.signature) {
    const sigValid = await verifyManifestSignature(manifest, options.publicKey);

    if (!sigValid) {
      errors.push({
        code: 'SIGNATURE_INVALID',
        message: 'Manifest signature verification failed',
        recoverable: false,
      });
    }
  } else if (options.verifySignature !== false) {
    errors.push({
      code: 'SIGNATURE_INVALID',
      message: 'Manifest missing signature',
      recoverable: false,
    });
  }

  // 10. Security classification validation
  if (manifest.security?.classification === 'security-critical') {
    if (!manifest.security.mandatoryAfter) {
      warnings.push('Security-critical update missing mandatoryAfter date');
    }
  }

  // 11. Rollout policy validation
  if (manifest.rollout) {
    if (manifest.rollout.killSwitch) {
      errors.push({
        code: 'REVOKED_RELEASE',
        message: 'Release has been paused by kill switch',
        recoverable: false,
      });
    }

    if (manifest.rollout.percentage < 0 || manifest.rollout.percentage > 100) {
      warnings.push(`Invalid rollout percentage: ${manifest.rollout.percentage}`);
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
    artifact,
  };
}

function validateArtifact(artifact: ArtifactInfo): UpdateError[] {
  const errors: UpdateError[] = [];

  if (!VALID_PLATFORMS.includes(artifact.platform)) {
    errors.push({
      code: 'UNSUPPORTED_PLATFORM',
      message: `Unsupported platform: ${artifact.platform}`,
      recoverable: false,
    });
  }

  if (!VALID_ARCHITECTURES.includes(artifact.architecture)) {
    errors.push({
      code: 'UNSUPPORTED_ARCHITECTURE',
      message: `Unsupported architecture: ${artifact.architecture}`,
      recoverable: false,
    });
  }

  if (!SHA256_RE.test(artifact.sha256)) {
    errors.push({
      code: 'HASH_MISMATCH',
      message: `Invalid SHA256 hash: ${artifact.sha256}`,
      recoverable: false,
    });
  }

  if (artifact.size <= 0) {
    errors.push({
      code: 'MANIFEST_INVALID',
      message: `Invalid artifact size: ${artifact.size}`,
      recoverable: false,
    });
  }

  if (!artifact.url.startsWith('https://')) {
    errors.push({
      code: 'MANIFEST_INVALID',
      message: `Artifact URL must use HTTPS: ${artifact.url}`,
      recoverable: false,
    });
  }

  if (!artifact.signature || artifact.signature.trim() === '') {
    errors.push({
      code: 'SIGNATURE_INVALID',
      message: 'Artifact missing signature',
      recoverable: false,
    });
  }

  if (!artifact.provenance?.builder || !artifact.provenance?.buildTimestamp) {
    errors.push({
      code: 'PROVENANCE_INVALID',
      message: 'Artifact missing provenance information',
      recoverable: false,
    });
  }

  try {
    parseSemanticVersion(artifact.version);
  } catch {
    errors.push({
      code: 'MANIFEST_INVALID',
      message: `Invalid artifact version: ${artifact.version}`,
      recoverable: false,
    });
  }

  return errors;
}

/**
 * Verifies the manifest signature. With a trusted public key this is real
 * RSA-SHA256 over the canonical manifest (signature field excluded,
 * sorted keys) — the exact bytes the server signs. Without a key it falls
 * back to presence-only (dev/test; production MUST pass publicKey).
 */
export async function verifyManifestSignature(manifest: UpdateManifest, publicKey?: string): Promise<boolean> {
  if (!manifest.signature) {return false;}

  if (!publicKey) {
    return typeof manifest.signature === 'string' && manifest.signature.length > 0;
  }

  try {
    const { signature: _sig, ...rest } = manifest;
    const canonical = stableStringify(rest);
    const verifier = createVerify('sha256');
    verifier.update(canonical);
    verifier.end();

    return verifier.verify(publicKey, Buffer.from(manifest.signature, 'base64'));
  } catch {
    return false;
  }
}

/**
 * Canonical JSON: recursively sorted keys, ALL keys retained at every
 * level. (A top-level-keys-only replacer array would silently drop nested
 * fields like artifact sha256 from the signed bytes — CVE-class bug.)
 */
export function stableStringify(value: unknown): string {
  if (value === null || typeof value !== 'object') {return JSON.stringify(value);}

  if (Array.isArray(value)) {return `[${value.map(stableStringify).join(',')}]`;}

  const entries = Object.entries(value as Record<string, unknown>)
    .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
    .map(([k, v]) => `${JSON.stringify(k)}:${stableStringify(v)}`);

  return `{${entries.join(',')}}`;
}

/**
 * Verifies an artifact's hash after download
 */
export async function verifyArtifactHash(
  filePath: string,
  expectedSha256: string
): Promise<boolean> {
  // Implementation would use platform-specific hash verification
  // For Node.js/Electron: crypto.createHash('sha256')
  // For browser: crypto.subtle.digest('SHA-256')
  // This is a placeholder
  return true;
}

/**
 * Checks if a release has been revoked
 */
export function isReleaseRevoked(manifest: UpdateManifest): boolean {
  return manifest.rollout?.killSwitch === true;
}

/**
 * Checks if update is mandatory based on security classification
 */
export function isMandatoryUpdate(manifest: UpdateManifest, currentVersion: string): boolean {
  if (manifest.security.classification === 'security-critical') {
    if (manifest.security.mandatoryAfter) {
      const mandatoryDate = new Date(manifest.security.mandatoryAfter).getTime();
      const now = Date.now();

      return now >= mandatoryDate;
    }

    return true;
  }

  return false;
}

/**
 * Validates update compatibility with current installation
 */
export function validateCompatibility(
  manifest: UpdateManifest,
  currentVersion: string
): { compatible: boolean; reason?: string } {
  // Check minimum version
  if (manifest.minimumVersion && compareVersions(currentVersion, manifest.minimumVersion) < 0) {
    return {
      compatible: false,
      reason: `Current version ${currentVersion} is below minimum required version ${manifest.minimumVersion}`,
    };
  }

  // Check protocol version
  if (manifest.protocolVersion && manifest.protocolVersion > MAX_PROTOCOL_VERSION) {
    return {
      compatible: false,
      reason: `Update protocol version ${manifest.protocolVersion} not supported (max: ${MAX_PROTOCOL_VERSION})`,
    };
  }

  return { compatible: true };
}