# AETHEROS MASTER 79 — Blocked Tests

Clean VM/Sandbox unavailable: `WindowsSandbox.exe` absent, no
snapshot-capable VM, non-admin shell. Per §94, certification is BLOCKED.

| Test ID | Reason | Required infrastructure | Impact | Next action |
|---|---|---|---|---|
| W79-002 – W79-010 (NSIS install→reinstall) | no clean Windows env | Win11 VM + snapshot restore, or Sandbox | P0 — cannot certify NSIS | provision VM, transfer artifact, verify HOST_HASH==VM_HASH, run §16–§27 |
| W79-011 – W79-020 (MSI install→silent) | same | same + msiexec logging path | P0 — cannot certify MSI | same; capture /L*V log + ProductCode + exit codes |
| W79-021 – W79-024 (Portable) | same | clean dir (e.g. C:\AetherOSPortableTest) | P0 — cannot certify Portable | hash-verify, launch, smoke, restart, data-policy check |
| W79-025/026/027 (path/user/orphan) | same | clean VM + normal user + tasklist | P0/P1 | run §46–§54 on VM |
| W79-005/006/014/015/023 (IPC/backend live) | same | VM + packaged runtime only | P0 | safe-channel IPC + backend health on VM |
| W79-028 runtime half | no VM launch | VM + bundled-python import check | P1 | import elevenlabs/mistralai from installed layout |
| W79-029 runtime half | no VM launch | VM launch of all 3 artifacts | P0 parity | compare payloads at runtime |
| W79-035 live half | no VM | VM + IPC/security probes | P0 security | run Windows desktop security suite on VM |
| Signing/SmartScreen/Defender | unsigned + no VM | code-sign cert + clean VM | production trust BLOCKED | acquire cert, sign, re-verify (signtool verify /pa /v), record SmartScreen |
| SBOM / provenance attestation | CI-only, CI not executed here | CI run + attestation | BLOCKED/UNVERIFIED | run release workflow, verify attestations |
| Screenshots/video | no GUI executed | VM GUI session | none — omitted honestly | capture on VM when available |

Signing (§85): SIGNING = BLOCKED (no credentials). Does not invalidate host
technical checks but prevents production trust certification.
Update (§88): UPDATE = NOT_IMPLEMENTED (unchanged, no implementation added).
