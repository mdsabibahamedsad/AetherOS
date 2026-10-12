#!/usr/bin/env node
/**
 * rc-manifest.mjs — build an IMMUTABLE Release Candidate manifest.
 *
 * Inputs (env):
 *   RC_VERSION (e.g. 1.1.0-beta.1), RC_CHANNEL (beta|rc|...), ARTIFACT_INDEX
 *   (path to artifact-index.json from publish-release.mjs), SBOM_PATH,
 *   TEST_STATUS_JSON ({"suite":"pass|fail|blocked", ...}), KNOWN_ISSUES (JSON array),
 *   PLATFORM_COVERAGE (JSON object), OUT_DIR (default dist-publish/rc).
 *
 * Refuses to overwrite an existing RC file (immutability §6–§7).
 * Records: commit, version, releaseId, artifacts+hashes, SBOM hash,
 * provenance, test status, known issues, platform coverage, timestamp.
 */
import { readFile, writeFile, mkdir, stat } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { join } from 'node:path';
import { execFileSync } from 'node:child_process';
import { existsSync } from 'node:fs';

const version = process.env.RC_VERSION;
const channel = process.env.RC_CHANNEL ?? 'beta';
const outDir = process.env.OUT_DIR ?? 'dist-publish/rc';
if (!version || !/^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$/.test(version)) {
  console.error('BLOCKED: RC_VERSION must be semver (e.g. 1.1.0-beta.1)');
  process.exit(1);
}

let commit = process.env.GITHUB_SHA ?? '';
try {
  commit = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf-8' }).trim() || commit;
} catch { /* keep env value */ }
if (!commit) {
  console.error('BLOCKED: cannot determine source commit');
  process.exit(1);
}

const indexPath = process.env.ARTIFACT_INDEX ?? 'dist-publish/artifact-index.json';
if (!existsSync(indexPath)) {
  console.error(`BLOCKED: artifact index missing: ${indexPath} (run publish-release first)`);
  process.exit(1);
}
const index = JSON.parse(await readFile(indexPath, 'utf-8'));

const sbomPath = process.env.SBOM_PATH ?? 'sbom.spdx.json';
let sbomHash = null;
if (existsSync(sbomPath)) {
  sbomHash = createHash('sha256').update(await readFile(sbomPath)).digest('hex');
} else {
  console.error('BLOCKED: SBOM missing — beta requires SBOM per channel policy');
  process.exit(1);
}

const testStatus = process.env.TEST_STATUS_JSON ? JSON.parse(process.env.TEST_STATUS_JSON) : {};
const failed = Object.entries(testStatus).filter(([, v]) => v === 'fail');
if (failed.length > 0) {
  console.error(`BLOCKED: required suites failing: ${failed.map(([k]) => k).join(',')}`);
  process.exit(1);
}

const rc = {
  product: 'AetherOS',
  kind: 'release-candidate',
  version,
  channel,
  releaseId: `aetheros-${version}`,
  commit,
  buildId: process.env.GITHUB_RUN_ID ?? 'local',
  artifacts: index.artifacts,
  sbom: { path: sbomPath, sha256: sbomHash },
  provenance: {
    workflow: 'update-release.yml',
    builder: 'AetherOS',
    buildTimestamp: new Date().toISOString(),
  },
  testStatus,
  knownIssues: process.env.KNOWN_ISSUES ? JSON.parse(process.env.KNOWN_ISSUES) : [],
  platformCoverage: process.env.PLATFORM_COVERAGE ? JSON.parse(process.env.PLATFORM_COVERAGE) : {},
  frozenAt: new Date().toISOString(),
};

await mkdir(outDir, { recursive: true });
const outPath = join(outDir, `${rc.releaseId}.json`);
try {
  await stat(outPath);
  console.error(`BLOCKED: RC already exists and is immutable: ${outPath} (bump version for a new RC)`);
  process.exit(1);
} catch (e) {
  if (e.code !== 'ENOENT') {
    throw e;
  }
}
await writeFile(outPath, JSON.stringify(rc, null, 2));
const digest = createHash('sha256').update(JSON.stringify(rc)).digest('hex');
console.log(`RC frozen: ${rc.releaseId} commit=${commit.slice(0, 12)} artifacts=${rc.artifacts.length} rc-sha256=${digest}`);
