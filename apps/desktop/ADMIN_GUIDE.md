# AetherOS Desktop Administrator Guide

## Overview
Guide for IT administrators deploying and managing AetherOS Desktop across enterprise environments.

## Deployment

### Mass Deployment

#### Windows (Group Policy / SCCM)
1. Download the MSI package: `Aetheros-{version}.msi`
2. Deploy via Group Policy:
   ```
   Computer Configuration → Software Settings → Software Installation → New → Package
   ```
3. Or deploy with SCCM:
   ```powershell
   # Create application in SCCM console
   # Deployment type: Windows Installer (*.msi file)
   # Installation command: msiexec /i "Aetheros-{version}.msi" /quiet /norestart
   ```

#### macOS (MDM)
1. Deploy via MDM (Jamf, Intune, Mosyle):
   - Upload the DMG package to your MDM
   - Set installation command:
   ```bash
   hdiutil attach Aetheros-{version}.dmg -mountpoint /tmp/aetheros
   cp -R /tmp/aetheros/AetherOS.app /Applications/
   hdiutil detach /tmp/aetheros
   ```

#### Linux (APT/YUM Repository)
```bash
# Add repository
sudo curl -fsSL https://aetheros.dev/repo/linux/gpg.key | sudo gpg --dearmor -o /etc/apt/keyrings/aetheros.gpg
echo "deb [signed-by=/etc/apt/keyrings/aetheros.gpg] https://aetheros.dev/repo/linux/stable /" | sudo tee /etc/apt/sources.list.d/aetheros.list
sudo apt-get update
sudo apt-get install aetheros-desktop
```

### Silent Installation
```powershell
# Windows NSIS
Aetheros-Setup-{version}.exe /S /D="C:\Program Files\AetherOS"

# Windows MSI
msiexec /i Aetheros-{version}.msi /quiet /norestart /log install.log

# macOS
sudo installer -pkg Aetheros-{version}.pkg -target /

# Linux (deb)
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y ./aetheros-{version}.deb
```

## Configuration

### Enterprise Policy File
Create `aetheros.policy.json` in the app configuration directory:

```json
{
  "update": {
    "channel": "stable",
    "autoUpdate": true,
    "allowedChannels": ["stable", "beta"]
  },
  "privacy": {
    "telemetry": true,
    "crashReporting": true
  },
  "security": {
    "allowedExtensions": [],
    "blockedExtensions": [],
    "sandboxEnabled": true,
    "networkAccess": "allow-all"
  },
  "workspace": {
    "defaultDirectory": "\\\\network\\share\\workspaces",
    "allowedDirectories": ["\\\\network\\share\\workspaces"],
    "autoSave": true,
    "autoSaveInterval": 60
  },
  "agents": {
    "allowedAgents": [],
    "defaultAgent": "assistant",
    "maxMemory": 1024,
    "maxCpu": 50
  },
  "updates": {
    "proxy": "http://proxy.company.com:8080",
    "verifySignature": true
  }
}
```

### Configuration via Environment Variables
```bash
# Update channel
AETHEROS_UPDATE_CHANNEL=stable

# Proxy configuration
AETHEROS_PROXY=http://proxy.company.com:8080
AETHEROS_PROXY_NO_PROXY=localhost,127.0.0.1

# Data directories
AETHEROS_CONFIG_DIR=/etc/aetheros
AETHEROS_DATA_DIR=/var/aetheros

# Debug/Verbose
AETHEROS_VERBOSE=1
AETHEROS_LOG_LEVEL=info
```

## Update Management

### Controlling Updates
- **Disable Auto-updates:** Set `"autoUpdate": false` in policy
- **Update Proxy:** Configure proxy for update downloads
- **Channel Control:** Restrict update channels via policy
- **Staged Rollouts:** Use the Beta channel for validation before Stable

### Verifying Update Integrity
```bash
# Verify signature of downloaded update
aetheros --verify-update Aetheros-Setup-{version}.exe

# Check current version and update status
aetheros --version
aetheros --check-update
```

## Security

### Code Signing Verification
```powershell
# Windows
Get-AuthenticodeSignature "C:\Program Files\AetherOS\AetherOS.exe"

# macOS
codesign -dvvv /Applications/AetherOS.app
spctl --assess --verbose /Applications/AetherOS.app

# Linux (deb)
dpkg-sig --verify aetheros-{version}.deb

# Linux (rpm)
rpm -K aetheros-{version}.rpm
```

### Audit Logging
AetherOS Desktop logs the following events:
- Application starts/stops
- User authentication
- Configuration changes
- Extension loading/unloading
- Update checks and installations
- Crash events

Log location: `~/.config/aetheros/logs/audit.log`

### Compliance
- **SOC 2:** Audit logging covers authentication, configuration changes
- **GDPR:** User data can be exported or deleted via Settings → Privacy
- **HIPAA:** Enable encryption and disable telemetry for healthcare deployments

## Monitoring

### Health Check Endpoint (localhost)
```bash
# Application health
curl http://localhost:48765/health

# Diagnostics dump
curl http://localhost:48765/diagnostics > diagnostics.json
```

### Integration with Monitoring Tools
- **Prometheus:** Metrics exposed at `/metrics` endpoint
- **Datadog:** Forward logs with the Datadog agent
- **Splunk:** Configure log forwarding to Splunk HTTP Event Collector

### Resource Monitoring Script
```bash
#!/bin/bash
# Monitor AetherOS resource usage
while true; do
  ps aux | grep AetherOS | grep -v grep
  sleep 60
done
```

## Troubleshooting

### Common Issues

**App won't start after update:**
1. Check deployment logs at `/var/log/aetheros-install.log`
2. Verify system compatibility
3. Rollback to previous version:
   ```powershell
   # Windows
   msiexec /i Aetheros-{previous-version}.msi /quiet /norestart
   ```

**Performance issues across fleet:**
1. Collect diagnostics: `aetheros --diagnostics > diagnostics.json`
2. Check system requirements are met
3. Verify no conflicting software (antivirus, proxy)
4. Review resource limits in policy configuration

**Update distribution fails:**
1. Verify connectivity to update server
2. Check proxy configuration
3. Ensure sufficient disk space
4. Review update logs: `~/.config/aetheros/logs/updater.log`

### Support Escalation
- **L1:** Local IT — installation, configuration, basic troubleshooting
- **L2:** AetherOS Admin Support — deployment, policy, security issues
- **L3:** AetherOS Engineering — bugs, crash analysis, feature requests

## Appendix

### Directory Layout
```
Windows:  %APPDATA%/AetherOS
macOS:    ~/Library/Application Support/AetherOS
Linux:    ~/.config/aetheros

Config:   ~/.config/aetheros/
Data:     ~/.local/share/aetheros/
Cache:    ~/.cache/aetheros/
Logs:     ~/.config/aetheros/logs/
```

### Ports
| Port | Protocol | Purpose |
|------|----------|---------|
| 48765 | TCP | Local HTTP API (health, metrics) |
| Dynamic | TCP | IPC between main and renderer |

### Exit Codes
| Code | Meaning |
|------|---------|
| 0 | Normal exit |
| 1 | General error |
| 2 | Configuration error |
| 3 | Runtime error |
| 4 | Crash recovered |
| 5 | Update required |
