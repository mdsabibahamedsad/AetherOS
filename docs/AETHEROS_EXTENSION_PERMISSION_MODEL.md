# Extension Permission Model (Master 44)

## Catalog (31 permissions, PermissionAPI v1)

R0–R1 read-only/limited data · R2 network/external · R3 file
modification · R4 execution/computer control · R5 credential/security.
Unknown permissions evaluate as R5/deny.

## Scopes (good vs bad)

- `filesystem.write {paths: [project/workspace/**]}` — never bare TRUE;
  `*` requires explicit `wildcard_approved`.
- `network.request {domains: [api.example.com]}` — subdomain match only
  (`evilapi.example.com` correctly denied).
- `browser.* {origins: [...]}` — fnmatch, no silent wildcard.
- `secrets.read_scoped/memory/mcp {names: [...]}` — exact scope names.

## Defaults & approval

Per-permission default (allow/deny/approve) + approval flag in catalog;
HIGH (R3) / CRITICAL (R4–R5) always surface in review UI with WHAT/WHY/
SCOPE/WHEN/RISK. Dangerous permissions are never behind "advanced" only —
`review_groups` returns all four bands together.

## Revocation

`revoke_all` drops in-memory grants (verified by post-revoke denial);
`revoke_everything` clears all extensions. Trust Center exposes grants,
scopes, MCP trust, logs, quarantine, revoke-all.
