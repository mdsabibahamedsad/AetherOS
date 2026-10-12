/**
 * Update Verifier — REAL artifact + manifest cryptography.
 *
 * Spec (§5–§6, §44–§46): SHA-256 (or stronger) digest check, RSA/EC
 * signature verification over artifact bytes and over the canonical
 * manifest, HTTPS-only URLs. No custom cryptography: node:crypto only.
 *
 * Manifest canonical form: JSON.stringify of the manifest WITHOUT the
 * `signature` field, with sorted keys. The server MUST sign that exact
 * form (see services/update/update-server.ts signManifest).
 */

import type { KeyLike } from 'node:crypto';
import { createHash, createVerify } from 'node:crypto';
import { createReadStream } from 'node:fs';
import { stat } from 'node:fs/promises';

import type { ArtifactInfo, UpdateManifest } from './types';

export function canonicalManifest(manifest: UpdateManifest): string {
  const { signature: _sig, ...rest } = manifest;

  return stableStringify(rest);
}

/** Canonical JSON: recursively sorted keys, all keys retained. */
export function stableStringify(value: unknown): string {
  if (value === null || typeof value !== 'object') {return JSON.stringify(value);}

  if (Array.isArray(value)) {return `[${value.map(stableStringify).join(',')}]`;}

  const entries = Object.entries(value as Record<string, unknown>)
    .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
    .map(([k, v]) => `${JSON.stringify(k)}:${stableStringify(v)}`);

  return `{${entries.join(',')}}`;
}

export function isHttpsUrl(url: string): boolean {
  try {
    return new URL(url).protocol === 'https:';
  } catch {
    return false;
  }
}

export async function sha256File(filePath: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const hash = createHash('sha256');
    const stream = createReadStream(filePath);
    stream.on('data', (chunk) => hash.update(chunk));
    stream.on('end', () => resolve(hash.digest('hex')));
    stream.on('error', reject);
  });
}

export function sha256Buffer(buffer: Uint8Array): string {
  return createHash('sha256').update(buffer).digest('hex');
}

export interface ArtifactVerification {
  valid: boolean;
  errors: string[];
}

/** Verify size + SHA-256 + HTTPS URL + RSA signature of a downloaded file. */
export async function verifyArtifactFile(
  artifact: ArtifactInfo,
  filePath: string,
  publicKey: string | KeyLike,
): Promise<ArtifactVerification> {
  const errors: string[] = [];

  if (!isHttpsUrl(artifact.url)) {
    errors.push(`Artifact URL must be HTTPS: ${artifact.url}`);
  }

  try {
    const info = await stat(filePath);

    if (info.size !== artifact.size) {
      errors.push(`Size mismatch: expected ${artifact.size}, got ${info.size}`);
    }
  } catch (e) {
    errors.push(`Cannot stat artifact file: ${e instanceof Error ? e.message : String(e)}`);

    return { valid: false, errors };
  }

  const digest = await sha256File(filePath);

  if (digest.toLowerCase() !== artifact.sha256.toLowerCase()) {
    errors.push('SHA-256 mismatch: artifact does not match manifest');

    return { valid: false, errors };
  }

  if (!artifact.signature) {
    errors.push('Artifact missing signature');

    return { valid: false, errors };
  }

  // Signature is over the raw artifact bytes.
  try {
    const { readFile } = await import('node:fs/promises');
    const bytes = await readFile(filePath);
    const verifier = createVerify('sha256');
    verifier.update(bytes);
    verifier.end();
    const ok = verifier.verify(publicKey, Buffer.from(artifact.signature, 'base64'));

    if (!ok) {errors.push('Artifact signature verification failed');}
  } catch (e) {
    errors.push(`Signature check error: ${e instanceof Error ? e.message : String(e)}`);
  }

  return { valid: errors.length === 0, errors };
}

/** Verify the manifest signature over its canonical form. */
export function verifyManifestSignature(manifest: UpdateManifest, publicKey: string | KeyLike): boolean {
  if (!manifest.signature) {return false;}

  try {
    const verifier = createVerify('sha256');
    verifier.update(canonicalManifest(manifest));
    verifier.end();

    return verifier.verify(publicKey, Buffer.from(manifest.signature, 'base64'));
  } catch {
    return false;
  }
}
