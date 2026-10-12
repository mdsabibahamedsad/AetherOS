# Extension Marketplace / Discovery (Master 44)

## What exists (real)

Local/bundled/remote/git/private/org sources with per-source trust
policy; registry index fetch with disk-cache fallback (ONLINE/OFFLINE/
REGISTRY_UNAVAILABLE explicitly reported); install flow with
verification; Extensions Center UI (installed/detail/security/events)
showing only existing metadata.

## What is NOT claimed

No download counts, ratings, reviews, or publisher-verified badges
unless the backing data exists — the UI has no such fields, so nothing
can be fabricated. Trust signals shown: signature state, publisher
trust, source, scan verdict, compat, permissions, version history.

## Private registries

Organization policy knobs: allowlist/blocklist, required signing,
required publisher, required scan, allowed/blocked permissions, allowed
sources, version pinning (`SourceManager` policies + `PublisherTrust`
org state). Air-gap = local packages + cached indexes (offline verified
by tests: fetch None + cache hit path).
