#!/usr/bin/env node
import { readFileSync, writeFileSync, existsSync } from 'fs';
import { execSync } from 'child_process';
import { resolve } from 'path';

const VERSION = process.env.VERSION || '0.0.0';
const ROOT = resolve(import.meta.dirname, '../..');

function getGitLog(base) {
  try {
    return execSync(`git log ${base}...HEAD --oneline --no-merges`, {
      cwd: ROOT, encoding: 'utf-8', maxBuffer: 10 * 1024 * 1024,
    }).trim().split('\n').filter(Boolean);
  } catch {
    return execSync('git log --oneline -100 --no-merges', {
      cwd: ROOT, encoding: 'utf-8', maxBuffer: 10 * 1024 * 1024,
    }).trim().split('\n').filter(Boolean);
  }
}

function loadChangelog() {
  const path = resolve(ROOT, 'CHANGELOG.md');
  if (!existsSync(path)) return '';
  const text = readFileSync(path, 'utf-8');
  const sections = text.split(/^## /m);
  return sections.length > 1 ? `## ${sections[1].trim()}` : text.slice(0, 3000);
}

const gitLog = getGitLog('v' + VERSION.replace(/-.*$/, '') || '');
const changelogSection = loadChangelog();
const date = new Date().toISOString().split('T')[0];

const notes = `# AetherOS Desktop v${VERSION}

**Release Date:** ${date}

## Overview
AetherOS Desktop v${VERSION} brings production-hardened stability, comprehensive testing,
enterprise security features, and cross-platform distribution readiness.

## What's New

${changelogSection || '* See CHANGELOG.md for details*'}

## Commits Since Previous Release
${gitLog.slice(0, 100).map(l => `- ${l}`).join('\n') || '* Initial release*'}

## Installation
- **Windows:** Download \`Aetheros-Setup-${VERSION}.exe\` or \`Aetheros-${VERSION}.msi\`
- **macOS:** Download \`Aetheros-${VERSION}.dmg\` or \`Aetheros-${VERSION}.zip\`
- **Linux:** Download \`Aetheros-${VERSION}.AppImage\`, \`aetheros-${VERSION}.deb\`, or \`aetheros-${VERSION}.rpm\`

## System Requirements
- **OS:** Windows 10+, macOS 12+, Ubuntu 22.04+ / Fedora 38+ / Arch Linux
- **CPU:** 64-bit, 2+ cores
- **RAM:** 4 GB minimum, 8 GB recommended
- **Storage:** 500 MB for app, additional for workspace data
- **GPU:** DirectX 12 / Metal / Vulkan support recommended

## Checksums
\`\`\`
*Checksums are generated during CI build and attached as release assets*
\`\`\`

## Security
- Code-signed binaries (Windows Authenticode, macOS notarized, Linux GPG)
- Encrypted token storage with OS keychain integration
- Sandboxed renderer processes with context isolation
- All communications over TLS 1.3

## Known Issues
- See RELEASE_CHECKLIST.md for any open items
- See GitHub Issues for tracked bugs

---

*Built from commit ${execSync('git rev-parse --short HEAD', { cwd: ROOT, encoding: 'utf-8' }).trim()}*
`;

writeFileSync(resolve(ROOT, 'release/RELEASE_NOTES.md'), notes, 'utf-8');
console.log(`Release notes generated for v${VERSION}`);
