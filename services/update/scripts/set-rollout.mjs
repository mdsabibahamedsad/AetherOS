#!/usr/bin/env node
/**
 * set-rollout.mjs — adjust the rollout percentage / kill switch for a release.
 * Requires UPDATE_ADMIN_URL + UPDATE_ADMIN_TOKEN. Fails closed when unset.
 * Usage: node set-rollout.mjs --percentage 100 [--kill | --resume]
 */
const adminUrl = (process.env.UPDATE_ADMIN_URL ?? '').replace(/\/$/, '');
const token = process.env.UPDATE_ADMIN_TOKEN;
const version = process.env.RELEASE_VERSION;
const channel = process.env.RELEASE_CHANNEL ?? 'stable';
if (!adminUrl || !token || !version) {
  console.error('BLOCKED: UPDATE_ADMIN_URL, UPDATE_ADMIN_TOKEN and RELEASE_VERSION are required');
  process.exit(1);
}
const args = process.argv.slice(2);
const pctIdx = args.indexOf('--percentage');
const percentage = pctIdx >= 0 ? Number(args[pctIdx + 1]) : 100;
if (!Number.isFinite(percentage) || percentage < 0 || percentage > 100) {
  console.error('BLOCKED: --percentage must be 0-100');
  process.exit(1);
}
const body = { version, channel, percentage };
if (args.includes('--kill')) body.killSwitch = true;
if (args.includes('--resume')) body.killSwitch = false;

const res = await fetch(`${adminUrl}/admin/rollout`, {
  method: 'PATCH',
  headers: { 'content-type': 'application/json', authorization: `Bearer ${token}` },
  body: JSON.stringify(body),
});
if (!res.ok) {
  console.error(`BLOCKED: rollout update failed: HTTP ${res.status} ${await res.text()}`);
  process.exit(1);
}
console.log(`Rollout for ${channel}@${version}: ${percentage}%${body.killSwitch === true ? ' KILLED' : ''}`);
