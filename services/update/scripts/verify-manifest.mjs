#!/usr/bin/env node
/**
 * verify-manifest.mjs — release gate: fetch the published manifest and
 * verify structure + signature + artifact URLs before rollout proceeds.
 * Any failure exits non-zero and stops the pipeline.
 */
import { createVerify } from 'node:crypto';

const url = process.env.UPDATE_MANIFEST_URL;
const pubkey = process.env.UPDATE_PUBKEY_PEM;
const version = process.env.RELEASE_VERSION;
if (!url || !pubkey || !version) {
  console.error('BLOCKED: UPDATE_MANIFEST_URL, UPDATE_PUBKEY_PEM and RELEASE_VERSION are required');
  process.exit(1);
}

const res = await fetch(url, { headers: { accept: 'application/json' } });
if (!res.ok) {
  console.error(`BLOCKED: manifest fetch failed: HTTP ${res.status}`);
  process.exit(1);
}
const manifest = await res.json();
const failures = [];
if (manifest.product !== 'AetherOS') failures.push('product != AetherOS');
if (manifest.version !== version) failures.push(`version ${manifest.version} != ${version}`);
if (manifest.protocolVersion !== 1) failures.push('protocolVersion != 1');
if (!manifest.signature) failures.push('missing manifest signature');
if (!Array.isArray(manifest.artifacts) || manifest.artifacts.length === 0) failures.push('no artifacts');

const { signature, ...rest } = manifest;
const canonical = stableStringify(rest);
function stableStringify(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(',')}]`;
  return `{${Object.entries(value).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0)).map(([k, v]) => `${JSON.stringify(k)}:${stableStringify(v)}`).join(',')}}`;
}
let sigOk = false;
try {
  sigOk = createVerify('sha256').update(canonical).end().verify(pubkey, Buffer.from(signature, 'base64'));
} catch (e) {
  failures.push(`signature verify error: ${e.message}`);
}
if (!sigOk) failures.push('manifest signature INVALID');

for (const a of manifest.artifacts ?? []) {
  if (!/^[0-9a-f]{64}$/i.test(a.sha256 ?? '')) failures.push(`bad sha256 for ${a.platform}-${a.architecture}`);
  if (!String(a.url ?? '').startsWith('https://')) failures.push(`non-https URL for ${a.platform}-${a.architecture}`);
  if (!a.signature) failures.push(`missing signature for ${a.platform}-${a.architecture}`);
}
if (manifest.rollout?.killSwitch) failures.push('killSwitch set on freshly published manifest');

if (failures.length > 0) {
  console.error(`BLOCKED: manifest verification failed:\n - ${failures.join('\n - ')}`);
  process.exit(1);
}
console.log(`Manifest ${manifest.releaseId} verified for ${version}`);
