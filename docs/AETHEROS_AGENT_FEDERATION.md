# Federation (Master 46 §§47–48, 115–116)

## Levels

`NONE → LOCAL → ORGANIZATION → TRUSTED_FEDERATION → PUBLIC_FEDERATION`,
configured per deployment. Public federation keeps strict trust
defaults: discovered records stay `discovered`/`unverified`, routing
modes `auto`/`federated` still require rank ≥ 2 for non-local candidates
and `highly_sensitive` data requires `fully_trusted` remotes.

## Organization record

`organizationId`, name, domains, identity provider, trusted agents,
policies, certificate authorities, allowed protocols. `organization_only`
routing requires membership **and** org-level trust. Tenant identity is
carried explicitly (`x-agent-id` + bearer token, checked against the
allowlist); it is never inferred from display names or URLs.

## Multi-tenancy

One endpoint may front many agents/workspaces. The server isolates by
allowlisted agent id; unknown ids are denied before any task logic runs
(tested: cross-tenant `message/send` rejected). Memory, artifacts,
credentials, and logs are keyed per agent; the audit trail records the
authenticated id on every event.

## Directory security

Registry entries carry provenance (`source`, fetch verification,
warnings). Display name, description, reviews, and ratings are
untrusted metadata — never identity proof, never authorization input.
