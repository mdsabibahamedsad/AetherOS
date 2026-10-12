#!/usr/bin/env node
import { execSync } from 'child_process';
import { readFileSync, writeFileSync } from 'fs';
import { resolve } from 'path';

const ROOT = resolve(import.meta.dirname, '../..');
const REPORT_PATH = resolve(ROOT, 'docs/DEPENDENCY_AUDIT.md');
const pkg = JSON.parse(readFileSync(resolve(ROOT, 'package.json'), 'utf-8'));

const date = new Date().toISOString().split('T')[0];
const dependencies = { ...pkg.dependencies, ...pkg.devDependencies };
const depCount = Object.keys(dependencies).length;

function runAudit() {
  try {
    const output = execSync('npm audit --json', { cwd: ROOT, encoding: 'utf-8', maxBuffer: 10 * 1024 * 1024 });
    return JSON.parse(output);
  } catch (e) {
    try { return JSON.parse(e.stdout); } catch { return null; }
  }
}

function runOutdated() {
  try {
    const out = execSync('npm outdated --json', { cwd: ROOT, encoding: 'utf-8', maxBuffer: 10 * 1024 * 1024 });
    return JSON.parse(out);
  } catch (e) {
    try { return JSON.parse(e.stdout); } catch { return {}; }
  }
}

function analyzeLicenses() {
  try {
    const out = execSync(
      'npx license-checker --json --production --excludePrivatePackages',
      { cwd: ROOT, encoding: 'utf-8', maxBuffer: 10 * 1024 * 1024, timeout: 30000 }
    );
    return JSON.parse(out);
  } catch { return null; }
}

console.log('Running dependency audit...');
const audit = runAudit();
const outdated = runOutdated();
const licenses = analyzeLicenses();

const vulnCount = audit?.vulnerabilities ? Object.keys(audit.vulnerabilities).length : 0;
const highCritical = audit?.metadata?.vulnerabilities?.high || 0;
const criticalCount = audit?.metadata?.vulnerabilities?.critical || 0;
const outdatedCount = Object.keys(outdated).length;

let report = `# Dependency Audit Report

**Date:** ${date}
**Project:** AetherOS Desktop v${pkg.version}
**Total Dependencies:** ${depCount}

## Summary

| Metric | Value |
|--------|-------|
| Total dependencies | ${depCount} |
| Known vulnerabilities | ${vulnCount} |
| High severity | ${highCritical} |
| Critical severity | ${criticalCount} |
| Outdated packages | ${outdatedCount} |

## Vulnerabilities

`;

if (audit?.vulnerabilities) {
  for (const [name, info] of Object.entries(audit.vulnerabilities)) {
    report += `### ${name} (${info.severity})\n- **Package:** ${info.name}\n- **Severity:** ${info.severity}\n- **Installed:** ${info.range}\n- **Fix available:** ${info.fixAvailable ? 'Yes' : 'No'}\n- **Via:** ${info.via?.map(v => typeof v === 'string' ? v : v.source || v.name).join(', ') || 'N/A'}\n\n`;
  }
} else {
  report += 'No vulnerabilities found or audit data unavailable.\n\n';
}

report += `## Outdated Packages

| Package | Current | Wanted | Latest |
|---------|---------|--------|--------|
`;
for (const [name, info] of Object.entries(outdated)) {
  report += `| ${name} | ${info.current} | ${info.wanted} | ${info.latest} |\n`;
}
report += '\n';

if (licenses) {
  const licenseTypes = {};
  for (const [, info] of Object.entries(licenses)) {
    const lic = info.licenses || 'Unknown';
    licenseTypes[lic] = (licenseTypes[lic] || 0) + 1;
  }
  report += '## License Summary\n\n| License | Count |\n|---------|-------|\n';
  for (const [lic, count] of Object.entries(licenseTypes).sort((a, b) => b[1] - a[1])) {
    report += `| ${lic} | ${count} |\n`;
  }
  report += '\n';
}

const score = Math.max(0, 100 - (highCritical * 5) - (criticalCount * 10) - outdatedCount);
report += `## Health Score: ${score}/100

| Range | Assessment |
|-------|-----------|
| 90-100 | Excellent |
| 70-89 | Good |
| 50-69 | Fair |
| <50 | Poor |

## Recommendations

${highCritical > 0 || criticalCount > 0 ? '- **URGENT:** Fix high/critical severity vulnerabilities immediately\n' : '- No urgent vulnerabilities found\n'}
${outdatedCount > 5 ? '- Update outdated packages to reduce technical debt\n' : ''}
- Review licenses for compatibility with distribution requirements
- Run regular audits (weekly via CI/CD)
`;

writeFileSync(REPORT_PATH, report, 'utf-8');
console.log(`\nReport written to ${REPORT_PATH}`);
console.log(`Vulnerabilities: ${vulnCount} (${highCritical} high, ${criticalCount} critical)`);
console.log(`Outdated: ${outdatedCount}`);
console.log(`Score: ${score}/100`);

if (highCritical > 0 || criticalCount > 0) process.exit(2);
