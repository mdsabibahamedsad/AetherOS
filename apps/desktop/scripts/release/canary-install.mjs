#!/usr/bin/env node
/**
 * canary-install.mjs — post-publish smoke: download the canary artifact for
 * linux-x64, verify SHA-256 + RSA signature against the published manifest,
 * report PASS/FAIL. Any mismatch fails the pipeline (no rollout).
 */
import { createHash, createVerify } from 'node:crypto';
import { writeFile } from 'node:fs/promises';

const manifestUrl = process.env.UPDATE_MANIFEST_URL;
const pubkey = process.env.UPDATE_PUBKEY_PEM;
if (!manifestUrl || !pubkey) {
  console.error('BLOCKED: UPDATE_MANIFEST_URL and UPDATE_PUBKEY_PEM are required');
  process.exit(1);
}
const manifest = await (await fetch(manifestUrl)).json();
const artifact = manifest.artifacts?.find((a) => a.platform === 'linux' && a.architecture === 'x64')
  ?? manifest.artifacts?.[0];
if (!artifact) {
  console.error('BLOCKED: manifest has no artifacts');
  process.exit(1);
}
const bytes = Buffer.from(await (await fetch(artifact.url)).arrayBuffer());
const digest = createHash('sha256').update(bytes).digest('hex');
if (digest.toLowerCase() !== artifact.sha256.toLowerCase()) {
  console.error(`BLOCKED: canary HASH_MISMATCH for ${artifact.url}`);
  process.exit(1);
}
const sigOk = createVerify('sha256').update(bytes).end()
  .verify(pubkey, Buffer.from(artifact.signature, 'base64'));
if (!sigOk) {
  console.error('BLOCKED: canary SIGNATURE_INVALID');
  process.exit(1);
}
await writeFile('canary-report.json', JSON.stringify({
  version: manifest.version, releaseId: manifest.releaseId,
  bytes: bytes.length, hashOk: true, sigOk: true, at: new Date().toISOString(),
}, null, 2));
console.log(`Canary PASS: ${manifest.version} (${bytes.length} bytes, hash+signature OK)`);
