#!/usr/bin/env node
/**
 * publish-manifest.mjs — build + sign the update manifest, then publish it.
 *
 * Inputs: dist-publish/artifact-index.json (from publish-release.mjs).
 * Signing key: UPDATE_SIGNING_KEY_PEM (private key PEM, from secrets).
 * Manifest signature = RSA-SHA256 over canonical JSON (sorted keys,
 * signature field excluded) — the exact form clients verify.
 * Without the key: BLOCKED, never published unsigned.
 */
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { createSign, randomBytes } from 'node:crypto';
import { execFileSync } from 'node:child_process';

const version = process.env.RELEASE_VERSION;
const channel = process.env.RELEASE_CHANNEL ?? 'beta';
const rolloutPct = Number(process.env.ROLLOUT_PERCENTAGE ?? '5');
const keyPem = process.env.UPDATE_SIGNING_KEY_PEM;
if (!version) {
  console.error('BLOCKED: RELEASE_VERSION required');
  process.exit(1);
}
if (!keyPem) {
  console.error('BLOCKED: UPDATE_SIGNING_KEY_PEM not set — refusing to publish unsigned manifest');
  process.exit(1);
}

const baseUrl = (process.env.ARTIFACT_BASE_URL ?? 'https://releases.aetheros.com').replace(/\/$/, '');
if (!baseUrl.startsWith('https://')) {
  console.error('BLOCKED: ARTIFACT_BASE_URL must be https');
  process.exit(1);
}

const index = JSON.parse(await readFile('dist-publish/artifact-index.json', 'utf-8'));
const commit = process.env.GITHUB_SHA ?? 'unknown';
const releaseId = randomBytes(16).toString('hex');
const platforms = {};
const artifacts = index.artifacts.map((a) => {
  const entry = {
    platform: platformId(a.platform),
    architecture: a.arch,
    version,
    buildId: process.env.GITHUB_RUN_ID ?? 'local',
    sourceCommit: commit,
    sha256: a.sha256,
    size: a.size,
    signature: signBytesPlaceholder(a),
    url: `${baseUrl}/desktop/${version}/${a.file}`,
    provenance: {
      builder: 'AetherOS',
      buildTimestamp: new Date().toISOString(),
      buildWorkflow: 'update-release.yml',
      dependencies: [],
    },
    packaging: packagingFor(a.platform),
  };
  platforms[`${entry.platform}-${entry.architecture}`] = entry;
  return entry;
});

// Sign each artifact digest with the release key (proves publisher identity).
for (const art of artifacts) {
  art.signature = rsaSign(Buffer.from(art.sha256, 'utf-8'), keyPem);
}

const manifest = {
  product: 'AetherOS',
  version,
  channel,
  releaseId,
  commit,
  platforms,
  minimumVersion: process.env.MINIMUM_SUPPORTED_VERSION ?? '1.0.0',
  artifacts,
  releaseNotes: process.env.RELEASE_NOTES ?? '',
  security: { classification: process.env.SECURITY_CLASSIFICATION ?? 'normal' },
  rollout: {
    percentage: rolloutPct,
    startDate: new Date().toISOString(),
  },
  protocolVersion: 1,
  timestamp: new Date().toISOString(),
  signature: '',
};
manifest.signature = rsaSign(Buffer.from(canonical(manifest), 'utf-8'), keyPem);

await mkdir('dist-publish/manifest', { recursive: true });
await writeFile(`dist-publish/manifest/${channel}.json`, JSON.stringify(manifest, null, 2));
console.log(`Manifest ${releaseId} signed for ${channel} @ ${version}`);

const uploadUrl = process.env.UPDATE_MANIFEST_URL;
if (!uploadUrl) {
  console.error('BLOCKED: UPDATE_MANIFEST_URL not set — manifest staged in dist-publish/manifest/, not published');
  process.exit(1);
}
execFileSync('curl', ['--fail', '-X', 'PUT', '-H', 'Content-Type: application/json', '--data-binary', `@dist-publish/manifest/${channel}.json`, uploadUrl], { stdio: 'inherit' });

function canonical(m) {
  const { signature: _s, ...rest } = m;
  return stableStringify(rest);
}
function stableStringify(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(',')}]`;
  return `{${Object.entries(value).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0)).map(([k, v]) => `${JSON.stringify(k)}:${stableStringify(v)}`).join(',')}}`;
}
function rsaSign(bytes, pem) {
  return createSign('sha256').update(bytes).end().sign(pem, 'base64');
}
function signBytesPlaceholder() {
  return '';
}
function platformId(p) {
  return p === 'win' ? 'win32' : p === 'mac' ? 'darwin' : 'linux';
}
function packagingFor(p) {
  return p === 'win' ? 'nsis' : p === 'mac' ? 'dmg' : 'appimage';
}
