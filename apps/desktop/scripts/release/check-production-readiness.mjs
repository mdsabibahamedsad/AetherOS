#!/usr/bin/env node
const checks = [
  { name: 'Version bumped beyond 0.x', test: () => {
    const pkg = JSON.parse(require('fs').readFileSync('package.json', 'utf-8'));
    return !pkg.version.startsWith('0.');
  }},
  { name: 'electron-builder config present', test: () => require('fs').existsSync('electron-builder.yml') },
  { name: 'Code signing configured', test: () => require('fs').existsSync('build/entitlements.mac.plist') },
  { name: 'Test scripts defined', test: () => {
    const pkg = JSON.parse(require('fs').readFileSync('package.json', 'utf-8'));
    return !!(pkg.scripts.test || pkg.scripts['test:ui'] || pkg.scripts.testall);
  }},
  { name: 'TypeScript strict mode', test: () => {
    const ts = JSON.parse(require('fs').readFileSync('tsconfig.json', 'utf-8'));
    return ts.compilerOptions?.strict === true;
  }},
  { name: 'ESLint configured', test: () =>
    require('fs').existsSync('.eslintrc.cjs') || require('fs').existsSync('.eslintrc.js') || require('fs').existsSync('eslint.config.mjs')
  },
  { name: 'Prettier configured', test: () => require('fs').existsSync('.prettierrc') || require('fs').existsSync('.prettierrc.json') },
  { name: '.gitignore exists', test: () => require('fs').existsSync('.gitignore') },
  { name: 'CHANGELOG.md exists', test: () => require('fs').existsSync('CHANGELOG.md') },
  { name: 'README.md exists', test: () => require('fs').existsSync('README.md') },
  { name: 'LICENSE file exists', test: () =>
    require('fs').existsSync('LICENSE') || require('fs').existsSync('LICENSE.txt')
  },
  { name: 'Code of Conduct exists', test: () =>
    require('fs').existsSync('CODE_OF_CONDUCT.md') || require('fs').existsSync('.github/CODE_OF_CONDUCT.md')
  },
  { name: 'Dockerfile or container support', test: () => require('fs').existsSync('Dockerfile') },
  { name: 'CI/CD workflows present', test: () =>
    require('fs').existsSync('../.github/workflows/desktop-build.yml')
  },
  { name: 'i18n/l10n support', test: () =>
    require('fs').existsSync('src/i18n') || require('fs').existsSync('src/locales')
  },
  { name: 'Crash recovery handler', test: () =>
    require('fs').existsSync('src/lib/crash-recovery.ts') || require('fs').existsSync('electron/crash-recovery.cjs')
  },
  { name: 'Auto-updater configured', test: () =>
    require('fs').existsSync('src/lib/auto-update.ts') || require('fs').existsSync('electron/auto-update.cjs')
  },
  { name: 'Security audit report exists', test: () =>
    require('fs').existsSync('SECURITY.md') || require('fs').existsSync('docs/SECURITY.md')
  },
  { name: 'Installation guide exists', test: () =>
    require('fs').existsSync('INSTALL.md') || require('fs').existsSync('docs/INSTALL.md')
  },
  { name: 'User guide exists', test: () =>
    require('fs').existsSync('USER_GUIDE.md') || require('fs').existsSync('docs/USER_GUIDE.md')
  },
];

let passed = 0, failed = 0;
console.log('\n=== Production Readiness Check ===\n');
for (const check of checks) {
  let ok;
  try { ok = check.test(); } catch { ok = false; }
  const icon = ok ? 'PASS' : 'FAIL';
  if (ok) passed++; else failed++;
  console.log(`  [${icon}] ${check.name}`);
}
console.log(`\n  Result: ${passed}/${checks.length} passed, ${failed} failed`);
console.log(`  Score: ${Math.round((passed / checks.length) * 100)}%\n`);
process.exit(failed > 0 ? 1 : 0);
