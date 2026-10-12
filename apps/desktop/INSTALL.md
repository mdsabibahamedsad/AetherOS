# AetherOS Desktop Installation Guide

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **Processor** | 64-bit dual-core, 2 GHz | 64-bit quad-core, 3 GHz+ |
| **RAM** | 4 GB | 8 GB+ |
| **Storage** | 500 MB free | 2 GB+ free |
| **Display** | 1280x720 | 1920x1080+ |
| **Internet** | Broadband required for initial setup | Broadband |

### Operating System Support

| OS | Version | Architectures |
|----|---------|--------------|
| **Windows** | 10 (21H2+), 11 | x64 |
| **macOS** | 12 Monterey+ | Intel x64, Apple Silicon (arm64) |
| **Ubuntu** | 22.04+ | x64 |
| **Debian** | 12+ | x64 |
| **Fedora** | 38+ | x64 |
| **Arch Linux** | Rolling | x64 |
| **openSUSE** | Tumbleweed | x64 |

## Installation

### Windows

#### Option 1: NSIS Installer (Recommended)
1. Download `Aetheros-Setup-{version}.exe` from the release page
2. Double-click the installer
3. Follow the setup wizard (defaults are recommended)
4. Launch from Start Menu or desktop shortcut

#### Option 2: MSI Installer (Enterprise)
1. Download `Aetheros-{version}.msi`
2. Deploy via Group Policy or SCCM:
   ```powershell
   msiexec /i Aetheros-{version}.msi /quiet /norestart
   ```
3. Per-user installation; no admin rights required

#### Silent Installation
```powershell
# NSIS
Aetheros-Setup-{version}.exe /S /D=C:\Program Files\AetherOS

# MSI
msiexec /i Aetheros-{version}.msi /quiet /norestart INSTALLDIR="C:\Program Files\AetherOS"
```

### macOS

#### Option 1: DMG (Recommended)
1. Download `Aetheros-{version}.dmg`
2. Open the DMG file
3. Drag the AetherOS app to the Applications folder
4. First launch: right-click → Open (Gatekeeper bypass for unsigned builds)
5. Signed builds open normally

#### Option 2: ZIP Archive
1. Download `Aetheros-{version}.zip`
2. Extract to Applications folder
3. Launch normally

#### Command Line
```bash
# DMG install
hdiutil attach Aetheros-{version}.dmg
cp -R /Volumes/AetherOS/AetherOS.app /Applications/
hdiutil detach /Volumes/AetherOS/

# ZIP install
unzip Aetheros-{version}.zip -d /Applications/
```

### Linux

#### AppImage (Universal)
```bash
chmod +x Aetheros-{version}.AppImage
./Aetheros-{version}.AppImage
```
Optionally move to `/opt` and create a desktop entry.

#### Debian/Ubuntu (deb)
```bash
sudo dpkg -i aetheros-{version}.deb
sudo apt-get install -f  # Fix dependencies
```

#### Fedora/RHEL (rpm)
```bash
sudo rpm -i aetheros-{version}.rpm
# Or
sudo dnf install aetheros-{version}.rpm
```

#### Arch Linux (AUR)
```bash
yay -S aetheros-desktop
```

## Post-Installation

### First Launch
1. Launch AetherOS Desktop
2. Complete the onboarding wizard
3. Sign in with your AetherOS account
4. Configure preferences

### Verification
```bash
# Check version
aetheros --version

# Run diagnostics
aetheros --diagnostics
```

## Updating

### Automatic Updates
1. AetherOS checks for updates on launch
2. Updates are downloaded and installed automatically
3. Restart to apply updates

### Manual Update
- Download the latest release and install over the existing installation
- User data is preserved during updates

### Update Channels
| Channel | Frequency | Stability |
|---------|-----------|-----------|
| Stable | Monthly | Production-ready |
| Beta | Bi-weekly | Feature-complete |
| Nightly | Daily | Experimental |

## Uninstallation

### Windows
```
Settings → Apps → AetherOS Desktop → Uninstall
```

### macOS
```
Finder → Applications → AetherOS → Trash
```

### Linux (deb)
```bash
sudo apt-get remove aetheros-desktop
```

### Linux (rpm)
```bash
sudo rpm -e aetheros-desktop
```

### Clean Removal
```bash
# Remove all user data (optional)
rm -rf ~/.config/aetheros
rm -rf ~/.local/share/aetheros
```

## Troubleshooting

### Installation Fails
- **Windows:** Run installer as Administrator, disable antivirus temporarily
- **macOS:** Check Gatekeeper: `spctl --assess --verbose /Applications/AetherOS.app`
- **Linux:** Install missing libraries: `sudo apt-get install libgtk-3-0 libwebkit2gtk-4.1-0`

### App Won't Launch
```bash
# Check logs
aetheros --verbose

# Reset configuration
aetheros --reset-config

# Safe mode (no extensions)
aetheros --safe-mode
```

### Support
- Documentation: https://aetheros.dev/docs
- Issues: https://github.com/aetheros/aetheros/issues
- Discord: https://discord.gg/aetheros
