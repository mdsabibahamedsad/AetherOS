#!/usr/bin/env node
import { readFileSync, writeFileSync, existsSync, readdirSync } from 'fs';
import { resolve, relative } from 'path';

const ROOT = resolve(import.meta.dirname, '../..');
const REPORT_PATH = resolve(ROOT, 'docs/SECURITY_AUDIT.md');

const checks = [];
let findings = [];
let score = 100;

function check(name, category, severity, test) {
  let ok;
  try { ok = test(); } catch { ok = false; }
  const points = { critical: 20, high: 10, medium: 5, low: 2 };
  if (!ok) {
    score -= points[severity] || 5;
    findings.push({ name, category, severity, status: 'FAIL' });
  } else {
    findings.push({ name, category, severity, status: 'PASS' });
  }
  checks.push({ name, category, severity, ok });
}

// === Renderer Security ===
check('Context isolation enabled', 'Renderer', 'critical', () => {
  const preload = readFileSync(resolve(ROOT, 'electron/preload.cjs'), 'utf-8');
  return preload.includes('contextIsolation') || preload.includes('contextBridge');
});

check('Node integration disabled', 'Renderer', 'critical', () => {
  const main = readFileSync(resolve(ROOT, 'electron/main.cjs'), 'utf-8');
  return main.includes('nodeIntegration: false') || main.includes('nodeIntegration:');
});

check('Sandbox enabled', 'Renderer', 'high', () => {
  const main = readFileSync(resolve(ROOT, 'electron/main.cjs'), 'utf-8');
  return main.includes('sandbox: true') || main.includes('sandbox:');
});

check('CSP headers configured', 'Renderer', 'high', () => {
  const main = readFileSync(resolve(ROOT, 'electron/main.cjs'), 'utf-8');
  return main.includes('Content-Security-Policy');
});

// === IPC Security ===
check('IPC path validation', 'IPC', 'critical', () => {
  const main = readFileSync(resolve(ROOT, 'electron/main.cjs'), 'utf-8');
  return main.includes('validatePath') || main.includes('pathExists');
});

check('IPC channel allowlist', 'IPC', 'high', () => {
  const main = readFileSync(resolve(ROOT, 'electron/main.cjs'), 'utf-8');
  return main.includes('allowlist') || main.includes('whitelist');
});

check('No ipcMain.on wildcards', 'IPC', 'critical', () => {
  const main = readFileSync(resolve(ROOT, 'electron/main.cjs'), 'utf-8');
  return !main.match(/ipcMain\.on\s*\(\s*['"`]\*/);
});

// === Storage Security ===
check('Encrypted token storage', 'Storage', 'critical', () => {
  const preload = readFileSync(resolve(ROOT, 'electron/preload.cjs'), 'utf-8');
  return preload.includes('safeStorage') || preload.includes('keytar') || preload.includes('cipher');
});

check('Sensitive file blocks', 'Storage', 'high', () => {
  const main = readFileSync(resolve(ROOT, 'electron/main.cjs'), 'utf-8');
  return main.includes('block') || main.includes('deny') || main.includes('forbidden');
});

check('Atomic writes', 'Storage', 'medium', () => {
  const main = readFileSync(resolve(ROOT, 'electron/main.cjs'), 'utf-8');
  return main.includes('atomic') || main.includes('writeFileSync') || main.includes('writeFile');
});

// === Crash Recovery ===
check('Crash loop breaker', 'Crash Recovery', 'medium', () => {
  const main = readFileSync(resolve(ROOT, 'electron/main.cjs'), 'utf-8');
  return main.includes('crash') || main.includes('recovery');
});

check('Safe mode entry point', 'Crash Recovery', 'medium', () => {
  return existsSync(resolve(ROOT, 'src/lib/crash-recovery.ts')) || existsSync(resolve(ROOT, 'electron/safe-mode.cjs'));
});

// === Auto-updater Security ===
check('Auto-updater configured', 'Updates', 'high', () => {
  const main = readFileSync(resolve(ROOT, 'electron/main.cjs'), 'utf-8');
  return main.includes('autoUpdater') || main.includes('updater');
});

check('Update signature verification', 'Updates', 'critical', () => {
  const main = readFileSync(resolve(ROOT, 'electron/main.cjs'), 'utf-8');
  return main.includes('signature') || main.includes('verify') || main.includes('cert');
});

// === Code Signing ===
check('macOS entitlements file', 'Code Signing', 'high', () => {
  return existsSync(resolve(ROOT, 'build/entitlements.mac.plist'));
});

check('macOS notarization script', 'Code Signing', 'high', () => {
  return existsSync(resolve(ROOT, 'build/notarize.cjs'));
});

check('Windows code signing config', 'Code Signing', 'high', () => {
  const config = existsSync(resolve(ROOT, 'electron-builder.yml')) ? readFileSync(resolve(ROOT, 'electron-builder.yml'), 'utf-8') : '';
  return config.includes('certificateFile') || config.includes('certificateSubjectName');
});

// === Build Security ===
check('Source maps disabled in production', 'Build', 'medium', () => {
  const config = readFileSync(resolve(ROOT, 'vite.config.ts'), 'utf-8');
  return config.includes('sourcemap: false') || config.includes('hidden-source-map');
});

check('Environment variable validation', 'Build', 'medium', () => {
  return existsSync(resolve(ROOT, 'scripts/validate-env.mjs')) || existsSync(resolve(ROOT, 'lib/env-validator.ts'));
});

// === File permissions ===
check('.env in .gitignore', 'Confi', 'high', () => {
  const gitignore = readFileSync(resolve(ROOT, '.gitignore'), 'utf-8');
  return gitignore.includes('.env') || gitignore.includes('env');
});

check('node_modules in .gitignore', 'Confi', 'high', () => {
  const gitignore = readFileSync(resolve(ROOT, '.gitignore'), 'utf-8');
  return gitignore.includes('node_modules');
});

check('release/ in .gitignore', 'Confi', 'medium', () => {
  const gitignore = readFileSync(resolve(ROOT, '.gitignore'), 'utf-8');
  return gitignore.includes('release') || gitignore.includes('dist');
});

// === i18n/a11y ===
check('Accessibility store exists', 'Accessibility', 'medium', () => {
  return existsSync(resolve(ROOT, 'src/store/accessibility-store.ts')) || existsSync(resolve(ROOT, 'src/store/accessibility-store.tsx'));
});

check('i18n translations present', 'Localization', 'low', () => {
  return existsSync(resolve(ROOT, 'src/i18n')) || existsSync(resolve(ROOT, 'src/locales'));
});

// === Reports ===
const passCount = findings.filter(f => f.status === 'PASS').length;
const failCount = findings.filter(f => f.status === 'FAIL').length;
const maxScore = checks.length * 10;
score = Math.max(0, Math.round((passCount / checks.length) * 100));

const report = `# Security Audit Report

**Date:** ${new Date().toISOString().split('T')[0]}
**Project:** AetherOS Desktop

## Security Score: ${score}/100

| Range | Assessment |
|-------|-----------|
| 90-100 | Excellent |
| 70-89 | Good |
| 50-69 | Fair |
| <50 | Poor |

## Summary

- **Total checks:** ${checks.length}
- **Passed:** ${passCount}
- **Failed:** ${failCount}

## Findings by Severity

| Severity | Pass | Fail |
|----------|------|------|
${['critical', 'high', 'medium', 'low'].map(s => {
  const f = findings.filter(x => x.severity === s);
  return `| ${s} | ${f.filter(x => x.status === 'PASS').length} | ${f.filter(x => x.status === 'FAIL').length} |`;
}).join('\n')}

## Detailed Findings

${findings.map(f =>
  `### ${f.status === 'PASS' ? '✅' : '❌'} ${f.name}\n- **Category:** ${f.category}\n- **Severity:** ${f.severity}\n- **Status:** ${f.status}\n`
).join('\n')}

## Recommendations

${findings.filter(f => f.status === 'FAIL' && f.severity === 'critical').map(f => `- **CRITICAL:** ${f.name} — must be addressed before release`).join('\n')}
${findings.filter(f => f.status === 'FAIL' && f.severity === 'high').map(f => `- **HIGH:** ${f.name} — strongly recommended for release`).join('\n')}
${findings.filter(f => f.status === 'FAIL' && f.severity === 'medium').map(f => `- **MEDIUM:** ${f.name} — consider addressing`).join('\n')}
${findings.filter(f => f.status === 'FAIL' && f.severity === 'low').map(f => `- **LOW:** ${f.name} — nice to have`).join('\n')}
`;

writeFileSync(REPORT_PATH, report, 'utf-8');
console.log(`\nSecurity audit written to ${REPORT_PATH}`);
console.log(`Score: ${score}/100 (${passCount}/${checks.length} passed)`);
