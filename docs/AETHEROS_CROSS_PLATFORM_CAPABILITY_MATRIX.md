# AetherOS Cross-Platform Capability Matrix

Legend: NATIVE (on-device) / REMOTE (via control plane) / DELEGATED
(desktop/server executes) / UNSUPPORTED / UNVERIFIED-live.

| Capability | Windows | macOS | Linux | iOS | iPadOS | Android | Web |
|---|---|---|---|---|---|---|---|
| agent execution | NATIVE | NATIVE | NATIVE | DELEGATED | DELEGATED | DELEGATED (contracts tested, app UNVERIFIED) | REMOTE |
| computer use | NATIVE (SendInput) | NATIVE (cua/AX) | NATIVE (X11; Wayland portal-only) | DELEGATED (monitor) | DELEGATED | DELEGATED (monitor) | REMOTE |
| screen capture | NATIVE | NATIVE (TCC) | NATIVE/portal | DELEGATED view | DELEGATED view | DELEGATED view | REMOTE |
| voice/camera/mic | NATIVE | NATIVE | NATIVE | NATIVE (UNVERIFIED) | NATIVE (UNVERIFIED) | NATIVE (UNVERIFIED) | partial |
| background runtime | NATIVE | NATIVE | NATIVE (systemd user) | constrained (BGTasks, UNVERIFIED) | constrained | constrained (WorkManager policy, UNVERIFIED) | n/a |
| notifications | NATIVE | NATIVE | NATIVE | APNs (UNVERIFIED) | APNs (UNVERIFIED) | FCM (UNVERIFIED) | in-app |
| memory/research | NATIVE | NATIVE | NATIVE | REMOTE browse | REMOTE browse | REMOTE browse | REMOTE |
| automation | NATIVE | NATIVE | NATIVE | monitor-only | monitor-only | monitor-only | REMOTE |
| MCP/A2A | NATIVE host | NATIVE host | NATIVE host | observe-only | observe-only | observe-only | REMOTE |
| device trust | device | device | device | device+attestation (UNVERIFIED) | same | device+integrity (UNVERIFIED) | session |

Desktop rows: implementation exists; live evidence per platform
certifications (Windows/macOS/Linux BETA). Mobile rows: contracts
tested; device evidence BLOCKED.
