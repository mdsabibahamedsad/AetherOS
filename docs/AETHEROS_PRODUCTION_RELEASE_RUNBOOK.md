# AetherOS Production Release Runbook (1.0)

1. source freeze (approved branch+commit+tag; any change → new RC)
2. audit (precertification matrix)
3. test (gates F01–F10; failures/blocks recorded, never overridden)
4. security (Master 72 regression + secret scan + entitlement review)
5. performance (Master 71 on prod bits; UNVERIFIED blocks promotion)
6. build (reproducible; digest recorded)
7. SBOM (generated + validated against artifact)
8. signing (creds-backed; fail-closed)
9. provenance (SLSA attestation generated)
10. attestation (`gh attestation verify` executed)
11. independent verification (second party re-verifies manifest+digests+sigs)
12. RC (immutable rc-manifest)
13. beta review (Master 74 exit criteria)
14. production approval (requester/reviewer/commit/version/security/QA/perf/supply-chain/timestamp; four-eyes where possible)
15. canary (1% + health gates)
16. staged rollout (5→10→25→50→100, auto-halt armed)
17. monitoring (1h/6h/24h/72h/7d reviews)
18. full rollout (only on sustained PASS)
19. post-release review (incidents, crashes, updates, support)

Release-day timeline T-24h…T+24h with check/decision/rollback-condition/owner
is executed from this runbook at launch; until then T-reviews are NOT_APPLICABLE.
