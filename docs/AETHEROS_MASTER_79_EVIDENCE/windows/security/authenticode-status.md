# Authenticode status — host evidence (W79-030)

Command: Get-AuthenticodeSignature on each artifact (2026-09-15, non-elevated).

- AetherOS-1.0.0-win-x64.exe → Status: NotSigned. "not digitally signed."
- AetherOS-1.0.0-win-x64-portable.exe → Status: NotSigned.
- AetherOS-1.0.0-win-x64.msi → Status: NotSigned.

SIGNATURE STATUS = UNSIGNED (all three). Expected: Master 78A has no signing
credentials. No signtool verification with a certificate was possible;
`signAndEditExecutable: false`, `verifyUpdateCodeSignature: false` in
build config confirm unsigned-by-design local build. SmartScreen trust: NO
CLAIM (UNVERIFIED / EXPECTED WARNING). Defender block/quarantine on clean
VM: UNVERIFIED.
