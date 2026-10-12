#!/usr/bin/env node
/**
 * Desktop integration test.
 * Usage: node scripts/test-desktop.mjs [--skip-build]
 */
import { execSync } from 'child_process';
import { existsSync, readdirSync } from 'fs';
import { resolve } from 'path';

const ROOT = resolve(import.meta.dirname, '..');
const skipBuild = process.argv.includes('--skip-build');

let exitCode = 0;

function run(name, cmd, opts = {}) {
  process.stdout.write(`  [ ] ${name}...`);
  try {
    execSync(cmd, {
      cwd: ROOT,
      stdio: 'pipe',
      timeout: opts.timeout || 120000,
      encoding: 'utf-8',
      ...opts,
    });
    console.log('\r  [✓] ' + name);
  } catch (e) {
    console.log('\r  [✗] ' + name);
    console.error(`       ${e.stderr?.substring(0, 300) || e.message}`);
    exitCode = 1;
  }
}

console.log('Desktop Integration Test\n');

// 1. Check build output
if (!skipBuild) {
  run('Build renderer', 'npm run build');
  run('TypeScript check', 'npm run typecheck');
  run('Lint', 'npm run lint');
}

// 2. Run unit tests
run('Vitest', 'npm run test:ui -- --run');

// 3. Run Electron module tests
run('Electron tests', 'node --test electron/*.test.cjs');

// 4. Verify package output (build.directories.output = dist-packaged)
const releaseDir = resolve(ROOT, 'dist-packaged');
if (existsSync(releaseDir)) {
  const files = readdirSync(releaseDir);
  console.log(`\n  Release artifacts (${files.length}):`);
  for (const f of files) {
    const size = existsSync(resolve(releaseDir, f))
      ? (execSync(`powershell -Command "(Get-Item '${resolve(releaseDir, f).replace(/'/g, "''")}').Length"`, { encoding: 'utf-8' }).trim() || '?')
      : '?';
    console.log(`    ${f} (${size} bytes)`);
  }
}

console.log(`\n${exitCode === 0 ? 'All tests passed!' : 'Some tests failed.'}`);
process.exit(exitCode);
