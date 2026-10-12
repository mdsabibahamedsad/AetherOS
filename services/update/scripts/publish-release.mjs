#!/usr/bin/env node
/**
 * publish-release.mjs — stage immutable release artifacts for upload.
 *
 * Reads packaged files from dist-packaged/, computes SHA-256, renames to
 *   AetherOS-{version}-{platform}-{arch}.{ext}
 * and writes dist-publish/artifacts/<file> + dist-publish/artifact-index.json.
 * Actual CDN upload happens via `aws s3 sync` when ARTIFACT_BUCKET is set;
 * otherwise the step stops BLOCKED (never pretends to publish).
 */
import { readdir, readFile, writeFile, mkdir, copyFile, stat } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { join, extname, basename } from 'node:path';
import { execFileSync } from 'node:child_process';
import { existsSync } from 'node:fs';

const version = process.env.RELEASE_VERSION;
const channel = process.env.RELEASE_CHANNEL ?? 'beta';
if (!version || !/^\d+\.\d+\.\d+/.test(version)) {
  console.error('BLOCKED: RELEASE_VERSION must be semver');
  process.exit(1);
}

const SRC = 'dist-packaged';
const DEST = 'dist-publish/artifacts';
if (!existsSync(SRC)) {
  console.error(`BLOCKED: ${SRC}/ missing — package step produced nothing`);
  process.exit(1);
}

const files = (await readdir(SRC, { recursive: true })).filter((f) => !f.endsWith('.map'));
if (files.length === 0) {
  console.error('BLOCKED: no packaged artifacts found');
  process.exit(1);
}

await mkdir(DEST, { recursive: true });
const index = [];
for (const rel of files) {
  const src = join(SRC, rel);
  if (!(await stat(src)).isFile()) continue;
  const ext = extname(rel);
  const plat = detectPlatform(rel);
  const arch = detectArch(rel);
  const name = `AetherOS-${version}-${plat}-${arch}${ext}`;
  const bytes = await readFile(src);
  const sha256 = createHash('sha256').update(bytes).digest('hex');
  await copyFile(src, join(DEST, name));
  index.push({ file: name, platform: plat, arch, size: bytes.length, sha256, channel });
  console.log(`${name}  ${sha256.slice(0, 16)}…  ${bytes.length} bytes`);
}
await writeFile('dist-publish/artifact-index.json', JSON.stringify({ version, channel, artifacts: index }, null, 2));

const bucket = process.env.ARTIFACT_BUCKET;
if (!bucket) {
  console.error('BLOCKED: ARTIFACT_BUCKET not set — artifacts staged in dist-publish/, upload not performed');
  process.exit(1);
}
execFileSync('aws', ['s3', 'sync', DEST, `${bucket}/desktop/${version}/`, '--cache-control', 'public, max-age=31536000, immutable'], { stdio: 'inherit' });
console.log(`Published ${index.length} artifacts to ${bucket}/desktop/${version}/`);

function detectPlatform(name) {
  const n = basename(name).toLowerCase();
  if (n.includes('win') || n.endsWith('.exe') || n.endsWith('.msi')) return 'win';
  if (n.includes('mac') || n.endsWith('.dmg') || n.endsWith('.pkg')) return 'mac';
  return 'linux';
}
function detectArch(name) {
  const n = basename(name).toLowerCase();
  if (n.includes('arm64')) return 'arm64';
  return 'x64';
}
