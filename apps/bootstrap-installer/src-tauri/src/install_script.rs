use std::path::PathBuf;

/// Install script resolution for self-contained AetherOS installer.
///
/// AetherOS is now a fully self-contained application. The installer bundles
/// everything needed (Electron, backend, Python runtime, dependencies) within
/// the installer executable itself. No external install scripts are downloaded
/// from GitHub or any other source.
///
/// This module is kept for API compatibility but always returns None —
/// indicating that no external script is required. All installation logic
/// is handled by the bundled package manager within the installer.
pub fn resolve_bundled_installer_path() -> Option<PathBuf> {
    None
}

pub fn requires_external_install_script() -> bool {
    false
}
