#!/usr/bin/env node
import { readFileSync, existsSync, readdirSync } from 'fs';
import { resolve } from 'path';

const ROOT = resolve(import.meta.dirname, '../..');
const SECRET_PATTERNS = [
  /(?:api[_-]?key|apikey|api[_-]?secret)['"]?\s*[:=]\s*['"].+['"]/gi,
  /(?:password|passwd|pwd)['"]?\s*[:=]\s*['"].+['"]/gi,
  /(?:secret|token|auth)['"]?\s*[:=]\s*['"].+['"]/gi,
  /(?:bearer\s+)[a-zA-Z0-9._-]+/gi,
  /(?:ghp_|gho_|ghu_|ghs_|ghr_)[a-zA-Z0-9]{36}/g,
  /(?:sk_live_|sk_test_|pk_live_|pk_test_)[a-zA-Z0-9]{24,}/g,
  /(?:xox[abpors]-)[a-zA-Z0-9-]{24,}/g,
  /(?:-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----)/g,
  /(?:AKIA[0-9A-Z]{16})/g,
];

const EXCLUDE_DIRS = ['node_modules', '.git', 'release', 'coverage', 'dist', '.next'];
const EXCLUDE_FILES = ['package-lock.json', '*.test.*', '*.spec.*', '*.map'];

function isExcluded(filePath) {
  const rel = filePath.replace(ROOT, '');
  for (const dir of EXCLUDE_DIRS) {
    if (rel.includes(dir)) return true;
  }
  for (const pattern of EXCLUDE_FILES) {
    if (pattern.startsWith('*.')) {
      if (rel.endsWith(pattern.slice(1))) return true;
    }
  }
  return rel.includes('node_modules') || rel.includes('.git');
}

function scanFile(filePath) {
  try {
    const content = readFileSync(filePath, 'utf-8');
    const findings = [];
    for (const pattern of SECRET_PATTERNS) {
      const matches = content.match(pattern);
      if (matches) {
        findings.push(...matches.map(m => ({
          file: filePath,
          match: m.substring(0, 40) + (m.length > 40 ? '...' : ''),
          pattern: pattern.toString().substring(0, 30),
        })));
      }
    }
    return findings;
  } catch {
    return [];
  }
}

function scanDir(dir) {
  let findings = [];
  try {
    const entries = readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const full = resolve(dir, entry.name);
      if (isExcluded(full)) continue;
      if (entry.isDirectory()) findings.push(...scanDir(full));
      else if (entry.isFile() && !entry.name.endsWith('.exe') && !entry.name.endsWith('.dll') && !entry.name.endsWith('.png') && !entry.name.endsWith('.jpg') && !entry.name.endsWith('.ico')) {
        findings.push(...scanFile(full));
      }
    }
  } catch {}
  return findings;
}

console.log('Scanning for potential secrets...');
const findings = scanDir(ROOT);

if (findings.length === 0) {
  console.log('No potential secrets found. Clean!');
  process.exit(0);
}

console.log(`\n⚠ Found ${findings.length} potential secret(s):\n`);
for (const f of findings) {
  console.log(`  File: ${f.file.replace(ROOT, '')}`);
  console.log(`  Match: ${f.match}`);
  console.log('');
}

console.log('Review each finding and remove or revoke any real secrets.');
process.exit(1);
