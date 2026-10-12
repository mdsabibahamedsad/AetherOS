# AetherOS Android Test Matrix / Release Manifest (68)

| Category | Command | Result |
|---|---|---|
| Android contracts | `pytest test_android_contract.py` | 6 passed (incl. manifest-file audit + host-spoof rejection) |
| Gradle build/tests | — | BLOCKED — no Java/Gradle/SDK |
| Emulator/device | — | BLOCKED — no hardware |
| AAB/signing/Play | — | BLOCKED — creds/toolchain |
| CI `android-platform.yml` | — | UNVERIFIED (not run) |

Manifest: package com.aetheros.android, minSdk 26, targetSdk 36
(declared, UNVALIDATED); no AAB produced; no signing; Play NOT
SUBMITTED. Known limitations: Kotlin unimplemented, FCM/Integrity
unconfigured, camera/mic/voice/TalkBack/battery untested, tablets/
foldables untested.
