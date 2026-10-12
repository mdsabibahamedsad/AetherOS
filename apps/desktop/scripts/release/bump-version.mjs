#!/usr/bin/env node
import { readFileSync, writeFileSync } from 'fs';
import { resolve } from 'path';

const ROOT = resolve(import.meta.dirname, '../..');
const MANIFEST_PATH = resolve(ROOT, 'package.json');

const TYPES = ['major', 'minor', 'patch', 'prerelease', 'premajor', 'preminor', 'prepatch'];
const type = process.argv[2] || 'patch';
if (!TYPES.includes(type)) {
  console.error(`Usage: bump-version.mjs <${TYPES.join('|')}>`);
  process.exit(1);
}

const pkg = JSON.parse(readFileSync(MANIFEST_PATH, 'utf-8'));
const current = pkg.version;
const parts = current.split(/[.-]/).map(Number);
let [major, minor, patch, prereleaseTag, prereleaseNum] = parts;

switch (type) {
  case 'major': major++; minor = 0; patch = 0; prereleaseTag = undefined; break;
  case 'minor': minor++; patch = 0; prereleaseTag = undefined; break;
  case 'patch': patch++; prereleaseTag = undefined; break;
  case 'prerelease':
    prereleaseNum = (prereleaseNum || 0) + 1;
    if (!prereleaseTag) { prereleaseTag = 1; prereleaseNum = 0; }
    break;
  case 'premajor': major++; minor = 0; patch = 0; prereleaseTag = 1; prereleaseNum = 0; break;
  case 'preminor': minor++; patch = 0; prereleaseTag = 1; prereleaseNum = 0; break;
  case 'prepatch': patch++; prereleaseTag = 1; prereleaseNum = 0; break;
}

const next = prereleaseTag ? `${major}.${minor}.${patch}-${prereleaseTag}.${prereleaseNum}` : `${major}.${minor}.${patch}`;
pkg.version = next;

writeFileSync(MANIFEST_PATH, JSON.stringify(pkg, null, 2) + '\n', 'utf-8');
console.log(`${current} → ${next}`);
