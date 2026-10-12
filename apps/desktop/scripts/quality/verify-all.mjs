#!/usr/bin/env node
import { execSync } from 'child_process';
import { resolve } from 'path';

const ROOT = resolve(import.meta.dirname, '../..');
const scripts = [
  { name: 'Lint', cmd: 'npm run lint' },
  { name: 'TypeScript', cmd: 'npm run typecheck' },
  { name: 'Unit tests', cmd: 'npm run test:ui -- --run' },
  { name: 'Build', cmd: 'npm run build' },
];

const results = [];
let allPass = true;

console.log('Running all verification checks...\n');

for (const { name, cmd } of scripts) {
  process.stdout.write(`  [ ] ${name}...`);
  try {
    execSync(cmd, { cwd: ROOT, stdio: 'pipe', timeout: 120000, encoding: 'utf-8' });
    console.log('\r  [✓] ' + name);
    results.push({ name, status: 'PASS' });
  } catch (e) {
    console.log('\r  [✗] ' + name);
    results.push({ name, status: 'FAIL', error: e.stderr?.substring(0, 500) || e.message });
    allPass = false;
  }
}

console.log('\n=== Summary ===');
for (const r of results) {
  console.log(`  [${r.status === 'PASS' ? '✓' : '✗'}] ${r.name}`);
  if (r.error) console.log(`       ${r.error}`);
}
console.log(`\n${allPass ? 'All checks passed!' : 'Some checks failed.'}`);
process.exit(allPass ? 0 : 1);
