#!/usr/bin/env node
/**
 * Performance BUDGET report generator (Master 24 P55/P56 honesty rules).
 *
 * Emits docs/PERFORMANCE_REPORT.md containing ONLY measured facts:
 *  - renderer bundle sizes from dist/assets when present
 *  - packaged installer sizes from dist-packaged when present
 * Everything else is NOT_MEASURED with its target preserved — never a
 * fabricated value or status.
 */
import { existsSync, readdirSync, statSync, writeFileSync } from 'fs';
import { resolve } from 'path';

const ROOT = resolve(import.meta.dirname, '../..');
const OUT = resolve(ROOT, 'docs/PERFORMANCE_REPORT.md');
const date = new Date().toISOString().split('T')[0];

const mb = (bytes) => (bytes / 1024 / 1024).toFixed(2);

function dirSizeBytes(dir, exts = null) {
  if (!existsSync(dir)) return null;
  let total = 0;
  let any = false;
  for (const entry of readdirSync(dir, { recursive: true })) {
    const p = resolve(dir, entry);
    try {
      const st = statSync(p);
      if (!st.isFile()) continue;
      if (exts && !exts.some((e) => entry.endsWith(e))) continue;
      total += st.size;
      any = true;
    } catch {
      /* unreadable entries skipped */
    }
  }
  return any ? total : null;
}

function row(label, bytes, targetMB = null) {
  const measured = bytes == null;
  const value = measured ? 'NOT_MEASURED' : `${mb(bytes)} MB`;
  const capped = targetMB != null && Number.isFinite(targetMB);
  const status = measured || !capped
    ? (measured ? '—' : 'INFO')
    : bytes <= targetMB * 1024 * 1024 ? 'PASS' : 'OVER';
  const target = capped ? `≤ ${targetMB} MB` : 'informational';
  return `| ${label} | ${value} | ${target} | ${status} |`;
}

const jsBytes = dirSizeBytes(resolve(ROOT, 'dist', 'assets'), ['.js']);
const cssBytes = dirSizeBytes(resolve(ROOT, 'dist', 'assets'), ['.css']);
// code-split apps: startup budget applies to the ENTRY chunk, not the
// sum of on-demand chunks — report both so neither can hide behind the other
let entryBytes = null;
const assetsDir = resolve(ROOT, 'dist', 'assets');
if (existsSync(assetsDir)) {
  for (const f of readdirSync(assetsDir)) {
    if (!/^index-.*\.js$/.test(f)) continue;
    try {
      const st = statSync(resolve(assetsDir, f));
      entryBytes = Math.max(entryBytes ?? 0, st.size);
    } catch { /* skip */ }
  }
}

const installerRows = [
  ['Windows NSIS', '.exe'],
  ['Windows MSI', '.msi'],
  ['macOS DMG', '.dmg'],
  ['Linux AppImage', '.AppImage'],
].map(([label, ext]) => {
  // top-level artifacts only — recursive scan double-counts unpacked payloads
  const dir = resolve(ROOT, 'dist-packaged');
  let bytes = null;
  if (existsSync(dir)) {
    for (const f of readdirSync(dir)) {
      if (!f.endsWith(ext)) continue;
      try {
        bytes = Math.max(bytes ?? 0, statSync(resolve(dir, f)).size);
      } catch { /* skip */ }
    }
  }
  return row(label, bytes, 200);
});

const report = `# Performance Budget Report

**Date:** ${date} · **Generator:** scripts/quality/benchmark-performance.mjs
**Host:** ${process.platform}/${process.arch} · node ${process.version}

## Honesty contract

Values below come ONLY from artifacts present on this machine at generation
time. Absent artifacts yield NOT_MEASURED with the target budget preserved —
never an assumed pass. Runtime metrics (startup, idle CPU/RAM, TTI) require
an interactive session of the built app (\`npm run profile:main\`) or CI
performance jobs.

## Bundle Budgets (from dist/assets)

| Metric | Measured | Target | Status |
|--------|----------|--------|--------|
${row('Renderer ENTRY chunk (startup payload)', entryBytes, 5)}
${row('Renderer JS total (all lazy chunks)', jsBytes, null)}
${row('Renderer CSS bundle', cssBytes, 1)}

## Installer Budgets (from dist-packaged)

| Artifact | Measured | Target | Status |
|----------|----------|--------|--------|
${installerRows.join('\n')}

## Runtime Budgets (targets — require interactive measurement)

| Metric | Target | Status |
|--------|--------|--------|
| Cold startup to interactive | < 3 s | NOT_MEASURED |
| Idle renderer RAM | < 150 MB | NOT_MEASURED |
| Idle CPU | < 2% | NOT_MEASURED |
| Command palette open | < 100 ms | NOT_MEASURED |
`;

writeFileSync(OUT, report);
console.log(`honest performance budget report written: ${OUT}`);
