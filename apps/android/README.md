# AetherOS Android app — SCAFFOLD, UNVERIFIED

No Java/Gradle/Android SDK exists in this workspace, so nothing here is
compiled or run. This scaffold declares the audited manifest contract
(`app/src/main/AndroidManifest.xml`, validated by
`audit_manifest()` in `aetheros_platform/android_contract.py`) and the
module layout. Kotlin implementation, Gradle build, emulator/device
testing, signing, and Play Console work are all BLOCKED and must be
done with a toolchain before any Android claim beyond this notice.

Layout (to be implemented):
- `app/` — Compose UI (Material 3, adaptive: phone/tablet/foldable)
- `domain/` — state machines, offline queue, idempotency (mirror
  `mobile_contract.py` + `android_contract.py` rules)
- `data/` — API client over the SAME backend routes as iOS (no second
  backend), Room/DataStore, Keystore-backed secrets
- No AccessibilityService, no daemon service, no WebView bridge.
