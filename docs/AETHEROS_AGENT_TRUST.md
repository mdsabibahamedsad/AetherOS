# Agent Trust (Master 46 §§11–13)

## Levels

| Level | Meaning | Privilege |
|---|---|---|
| `unknown` | never seen | none |
| `discovered` | card fetched/parsed | none — metadata only |
| `unverified` | structurally valid card | read-only task queries |
| `verified` | TLS + issuer/signature evidence, no mismatch | submit low-risk tasks |
| `user_trusted` | explicit user approval | scoped capabilities + approvals |
| `organization_trusted` | org IdP / admin approval | org skills, higher caps |
| `fully_trusted` | explicit maximum approval | all grantable capabilities (still never shell/secrets) |
| `blocked` | user/org block | new tasks denied |
| `revoked` | terminal | denied + pending tasks cancelled |

## Transition rules (`trust.py`)

Only explicit edges exist (`_ALLOWED_TRANSITIONS`); level-skipping is
rejected; `revoked` has no outgoing edges. Every change appends
`{from, to, by, at}` to the record history and is audit-logged.

## What trust is NOT

- Same brand/LAN/org/model/protocol ⇒ **nothing**. Trust is established,
  never assumed (tested: spoofed display names get distinct ids).
- Reputation (reliability scores, latency, success counts) is
  informational, task-class-specific, and time-decayed
  (`record_relationship` × 0.95 decay). It informs routing; it never
  upgrades trust or bypasses authorization.

## Agent Card verification labels

`UNVERIFIED` (default) / `VERIFIED` (TLS + signature-or-issuer, fresh,
endpoint-consistent) / `TRUSTED` (explicit user/org approval on top) /
`REVOKED`. The label is computed from evidence (`verification_label`),
never from a card merely fetching successfully. Sensitive card changes
(new endpoint, capabilities, permissions, publisher, auth schemes) set
`reverify_required` on the registry record.
