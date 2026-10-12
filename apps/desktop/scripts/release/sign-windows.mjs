#!/usr/bin/env node
/**
 * sign-windows.mjs — code-sign Windows artifacts.
 * Uses Azure Trusted Signing when AZURE_TRUSTED_SIGNING_* is configured,
 * else signtool with WINDOWS_SIGN_CERT (PFX base64) + timestamp server.
 * No credentials → BLOCKED (exit 1). Never marks unsigned builds as signed.
 */
import { readdir } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import { join } from 'node:path';

const dir = process.argv[2] ?? 'dist-packaged';
const azureAccount = process.env.AZURE_TRUSTED_SIGNING_ACCOUNT;
const pfxB64 = process.env.WINDOWS_SIGN_CERT;

const targets = [];
for (const f of await readdir(dir, { recursive: true })) {
  if (f.endsWith('.exe') || f.endsWith('.msi')) targets.push(join(dir, f));
}
if (targets.length === 0) {
  console.error('BLOCKED: no .exe/.msi artifacts to sign');
  process.exit(1);
}

if (azureAccount) {
  console.log('Signing via Azure Trusted Signing…');
  for (const t of targets) {
    execFileSync('az', ['codesigning', 'sign', '--file', t,
      '--account', azureAccount,
      '--certificate-profile', process.env.AZURE_TRUSTED_SIGNING_PROFILE ?? 'AetherOS',
      '--timestamp-url', 'http://timestamp.acs.microsoft.com'], { stdio: 'inherit' });
  }
} else if (pfxB64) {
  const { writeFileSync } = await import('node:fs');
  writeFileSync(`${dir}/sign-cert.pfx`, Buffer.from(pfxB64, 'base64'));
  try {
    for (const t of targets) {
      execFileSync('signtool', ['sign', '/f', `${dir}/sign-cert.pfx`,
        '/p', process.env.WINDOWS_SIGN_CERT_PASSWORD ?? '',
        '/tr', 'http://timestamp.digicert.com', '/td', 'sha256', '/fd', 'sha256', t],
        { stdio: 'inherit' });
    }
  } finally {
    const { rmSync } = await import('node:fs');
    rmSync(`${dir}/sign-cert.pfx`, { force: true });
  }
} else {
  console.error('SIGNING=BLOCKED: no Azure Trusted Signing or WINDOWS_SIGN_CERT configured');
  process.exit(1);
}
console.log(`Signed ${targets.length} Windows artifact(s)`);
