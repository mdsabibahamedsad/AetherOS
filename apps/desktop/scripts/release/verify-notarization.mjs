#!/usr/bin/env node
/**
 * verify-notarization.mjs — confirm Apple notarization staples on mac artifacts.
 * Runs `xcrun stapler validate` on every .dmg/.pkg/.app. Any failure or
 * missing xcrun on a mac-required run → BLOCKED. On non-mac CI this script
 * reports macOS=BLOCKED unless SKIP_MAC_VALIDATION=1 (local dev only).
 */
import { execFileSync } from 'node:child_process';
import { readdir } from 'node:fs/promises';
import { join } from 'node:path';
import { platform } from 'node:os';

const dir = process.argv[2] ?? 'dist-packaged';
if (platform() !== 'darwin') {
  if (process.env.SKIP_MAC_VALIDATION === '1') {
    console.log('macOS=BLOCKED (no mac runner); SKIP_MAC_VALIDATION=1 acknowledged for local dev');
    process.exit(0);
  }
  console.error('macOS=BLOCKED: notarization must be validated on a macOS runner');
  process.exit(1);
}
const targets = (await readdir(dir, { recursive: true })).filter((f) =>
  f.endsWith('.dmg') || f.endsWith('.pkg') || f.endsWith('.app'));
if (targets.length === 0) {
  console.error('BLOCKED: no mac artifacts to validate');
  process.exit(1);
}
for (const t of targets) {
  execFileSync('xcrun', ['stapler', 'validate', join(dir, t)], { stdio: 'inherit' });
}
console.log(`Notarization validated for ${targets.length} artifact(s)`);
