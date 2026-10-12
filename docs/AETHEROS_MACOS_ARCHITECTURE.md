# AetherOS macOS Architecture

Electron 40 app (`com.aetheros.aetheros`, `AetherOS`), DMG/ZIP/PKG ×
arm64+x64, Hardened Runtime on, `afterSign` notarization (secret-gated).
Renderer → typed preload → validated IPC → main → Python backend,
identical to Windows; mac specifics: `~/Library/*` satellite paths
(`aetheros_platform/macos_paths.py`, home stays `~/.aetheros`),
`aetheros://` scheme + `.aetheros/.aethskill/.aethcfg` associations,
cua-driver AX backend for computer-use, Keychain abstraction
(`macos_keychain.py`, SecItem live path BLOCKED), TCC capability model
(`macos_tcc.py`), capability registry via `windows_capabilities.py`
cross-platform detectors (rename pending — detectors are OS-aware).
No App Sandbox (see SANDBOX decision); direct Developer ID distribution.
