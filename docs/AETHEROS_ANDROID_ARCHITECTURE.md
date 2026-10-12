# AetherOS Android Architecture / Security / Background / Push / Offline / Privacy / Play

Client (scaffold, UNVERIFIED): `apps/android` manifest audited by
`audit_manifest()` (exact package, min26/target36, no unjustified
dangerous perms, no exported-without-permission, no typeless
foreground service, never debuggable/cleartext). Kotlin layers
pending toolchain. Backend: SAME api_server routes as iOS (no second
backend); contracts in `android_contract.py` (tested).

Background: WorkManager policy (constraints allowlist, expedited needs
justification — no daemon emulation); NO foreground service declared;
NO AccessibilityService (would be a bypass). Push: FCM minimal-preview
rules tested; APNs/FCM delivery BLOCKED. Offline: same classified
queue discipline as iOS. Privacy: secrets in Keystore (never
SharedPreferences), backup excludes secrets, no tracking. Play: Data
Safety + target-36 + policy audit documented, NOT submitted; Play
Integrity server-verified design, unconfigured.
