#!/usr/bin/env node
/**
 * revoke-release.mjs — revoke a release/artifact/channel/version (§66).
 * Calls the update-service admin API. Fail-closed: requires
 * UPDATE_ADMIN_URL + UPDATE_ADMIN_TOKEN + RELEASE_ID. Prints the
 * revocation receipt (releaseId, scope, timestamp).
 */
const adminUrl = (process.env.UPDATE_ADMIN_URL ?? '').replace(/\/$/, '');
const token = process.env.UPDATE_ADMIN_TOKEN;
const releaseId = process.env.RELEASE_ID;
const scope = process.argv[2] ?? 'release'; // release|artifact|channel|version
if (!adminUrl || !token || !releaseId) {
  console.error('BLOCKED: UPDATE_ADMIN_URL, UPDATE_ADMIN_TOKEN and RELEASE_ID are required');
  process.exit(1);
}
if (!['release', 'artifact', 'channel', 'version'].includes(scope)) {
  console.error('BLOCKED: scope must be release|artifact|channel|version');
  process.exit(1);
}
const reason = process.env.REVOKE_REASON ?? 'operator revocation';
const res = await fetch(`${adminUrl}/admin/revoke`, {
  method: 'POST',
  headers: { 'content-type': 'application/json', authorization: `Bearer ${token}` },
  body: JSON.stringify({ releaseId, scope, reason }),
});
if (!res.ok) {
  console.error(`BLOCKED: revocation failed: HTTP ${res.status} ${await res.text()}`);
  process.exit(1);
}
const receipt = await res.json();
console.log(`REVOKED scope=${scope} release=${releaseId} at=${receipt.at ?? new Date().toISOString()} reason=${reason}`);
