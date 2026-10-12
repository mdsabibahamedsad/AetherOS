# AetherOS 1.0.0 Release Notes (Production — WITHHELD)

Status: **NOT RELEASED — PRODUCTION BLOCKED.** This file documents what 1.0.0
would contain and why it is withheld. Nothing below claims availability.

## Intended content
- Universal auto-update with verified rollback; channel model
  (stable/beta/enterprise); signed feature flags; redacted support bundles.
- Desktop (Windows/Linux x64 first), update server, beta-tested logic paths.

## Why withheld (P0)
1. No signing credentials → no trustworthy artifact can exist.
2. No packaged build → nothing to install, verify, or deploy.
3. No device evidence → platform claims would be fabrication.

## Security / update / rollback / migration
Per Master 70.5 + 74 evidence (harness-tested, device-UNVERIFIED). No known
critical code vulnerability; B74-001 fixed. Migration: expand/contract policy;
legacy data never auto-destroyed.

## Known limitations
Everything in the beta notes, plus: this is a source release only.
