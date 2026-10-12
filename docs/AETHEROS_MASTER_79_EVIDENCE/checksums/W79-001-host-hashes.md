# W79-001 artifact hash verification — host-side evidence

Source commit (actual HEAD): 2bdfbfd8ebcf2bb27b06f600c2beb159e723d8b1
Computed on host 2026-09-15 via PowerShell Get-FileHash (SHA256).
Host paths: apps/desktop/dist-packaged/...

| Artifact | Size (bytes) | SHA-256 (host) | Baseline match |
|---|---|---|---|
| AetherOS-1.0.0-win-x64.exe (NSIS) | 195891460 | B86B22F74F1AFAA74BC28A304FF13E5BB0B0A6AD8CC42E969D138C34E67F9278 | YES — equals Master 78A baseline b86b22f7…f9278 |
| AetherOS-1.0.0-win-x64.msi | 203137784 | 1069FC6D26EE71810A9131F1383413D51252A3F3AE99C357F054DD1E2A5B031B | YES — equals baseline 1069fc6d…5b031b |
| AetherOS-1.0.0-win-x64-portable.exe | 162205111 | 214D425537EB8EEA43CA6C3F78F48EDC1CCCE758817E3FB9425E52CA143CFE3C | YES — equals baseline 214d4255…43cfe3c |

STATUS: PASSED (host-side identity only; VM_HASH comparison BLOCKED — no VM).
install-stamp.json (win-unpacked/resources): commit matches HEAD, dirty=true, source=local.
