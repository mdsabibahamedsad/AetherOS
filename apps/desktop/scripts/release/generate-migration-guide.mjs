#!/usr/bin/env node
import { writeFileSync, existsSync, readFileSync } from 'fs';
import { resolve } from 'path';

const ROOT = resolve(import.meta.dirname, '../..');
const FROM = process.argv[2] || '0.x';
const TO = process.argv[3] || '1.0.0';

const changelogPath = resolve(ROOT, 'CHANGELOG.md');
const changelog = existsSync(changelogPath) ? readFileSync(changelogPath, 'utf-8') : '';

function extractBreakingChanges(text) {
  const lines = text.split('\n');
  const breaking = [];
  for (const line of lines) {
    const lower = line.toLowerCase();
    if (lower.includes('breaking') || lower.includes('migration') || lower.includes('deprecat') || lower.includes('remove')) {
      breaking.push(line.trim().replace(/^[-*]\s*/, ''));
    }
  }
  return breaking;
}

const breaking = extractBreakingChanges(changelog);

const guide = `# Migration Guide: ${FROM} → ${TO}

## Overview
This guide covers the migration from ${FROM} to ${TO} of AetherOS Desktop.
Estimated migration time: 30-60 minutes.

## Breaking Changes

${breaking.map(b => `- ${b}`).join('\n') || '*No breaking changes detected*'}

## Configuration Migration

### Preferences
\`\`\`
# ${FROM} ~/.config/aetheros/preferences.json
# ${TO}   OS-native preferences (electron-store or Registry/UserDefaults)
\`\`\`

### Workspace Data
Workspace data format is backward-compatible. No migration needed.

### Tokens & Credentials
Tokens are now stored encrypted in the OS keychain:
- Windows: Credential Manager
- macOS: Keychain
- Linux: secret-service/libsecret

Legacy plaintext tokens will be migrated on first launch.

## API Changes

### Preload Bridge
- \`window.electronAPI.*\` → \`window.__HERMES_PRELOAD_API__.*\` (context isolation)

### IPC Channels
- \`hermes:*\` channels now validate origin against a allowlist
- Custom channels must be registered via \`registerChannel()\` in main process

## Plugin / Extension Changes
(No plugin system changes in this release)

## Rollback
To roll back to ${FROM}:
1. Uninstall ${TO}
2. Install ${FROM} from previous release
3. Restore preferences from backup

## Support
- Documentation: https://aetheros.dev/docs
- Issues: https://github.com/hermes-agent/aetheros/issues
- Discord: https://discord.gg/aetheros
`;

writeFileSync(resolve(ROOT, 'docs/MIGRATION_GUIDE.md'), guide, 'utf-8');
console.log(`Migration guide generated: ${FROM} → ${TO}`);
