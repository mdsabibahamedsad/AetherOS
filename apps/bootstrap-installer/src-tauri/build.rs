fn main() {
    // AetherOS is now a fully self-contained application. The installer bundles
    // everything needed (Electron, backend, Python runtime, all dependencies)
    // within the installer executable itself. No external install scripts are
    // downloaded from GitHub. No git commit/branch pinning is needed.

    // Build the Tauri application with the Windows manifest
    #[cfg(target_os = "windows")]
    let attrs = {
        let manifest = include_str!("aetheros-setup.manifest");
        let win = tauri_build::WindowsAttributes::new().app_manifest(manifest);
        tauri_build::Attributes::new().windows_attributes(win)
    };

    #[cfg(not(target_os = "windows"))]
    let attrs = tauri_build::Attributes::new();

    tauri_build::try_build(attrs).expect("failed to run tauri-build");
}
