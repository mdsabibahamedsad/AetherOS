# MSI metadata — host read-only query (W79-011 related, static only)

Method: WindowsInstaller.Installer COM OpenDatabase read-only, no install.

- File: apps/desktop/dist-packaged/AetherOS-1.0.0-win-x64.msi
- Property ProductCode: {77035F50-600E-49B1-851F-6E004FDBC134}
- install-stamp commit == HEAD (see checksums evidence).
- Portable VersionInfo: ProductName=AetherOS, ProductVersion=1.0.0,
  FileDescription="Native desktop shell for AetherOS."
- win-unpacked VersionInfo (AetherOS.exe): ProductName=AetherOS,
  ProductVersion=40.9.3 (= packaged Electron version, expected
  electron-builder behavior), LegalCopyright="(c) 2026 AetherOS".
- Product identity: appId com.aetheros.aetheros, productName AetherOS,
  executableName AetherOS, version 1.0.0 (apps/desktop/package.json + build).
- NSIS config: oneClick=false, perMachine=true (UAC prompt EXPECTED),
  allowToChangeInstallationDirectory=true, shortcutName=AetherOS,
  createDesktopShortcut=true, createStartMenuShortcut=true,
  uninstallDisplayName="AetherOS ${version}",
  deleteAppDataOnUninstall=false (user-data preservation is product policy;
  must NOT be scored as uninstall failure), runAfterFinish=true.
- No install/uninstall/repair/silent operations were executed on the host
  (dev machine, non-admin, not clean). All MSI operational tests BLOCKED.

# Window-title branding note (W79 follow-up, §61)

- electron/main.cjs BrowserWindow titles: 'AetherOS' (correct) —
  createSessionWindow (~line 4627) and createWindow (~line 4677).
- apps/desktop/index.html line 11: `<title>Aetheros</title>` (legacy
  spelling). Renderer document title can override the native title after
  load, so the "Aetheros" report from Master 78A is plausibly this line.
  Cosmetic P1; NOT fixed in Master 79 (no source changes per no-cheating /
  no-rebuild rule; fix + rebuild is a documented follow-up).
