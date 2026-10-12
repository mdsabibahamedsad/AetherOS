# AetherOS Update Troubleshooting Guide

## Quick Reference

| Symptom | Likely Cause | Solution |
|---------|--------------|----------|
| "No update available" but newer version exists | Channel mismatch, rollout percentage, cache | Check channel, wait for rollout, clear cache |
| Download fails repeatedly | Network, disk space, hash mismatch | Check network, free disk, clear download cache |
| Install fails with "Permission denied" | No admin/sudo, UAC disabled | Run as admin, enable UAC, check sudo |
| App won't launch after update | Health check failed, rollback needed | Check logs, manual rollback, reinstall |
| "Update signature invalid" | Corrupted download, wrong artifact | Re-download, verify manifest, check CDN |
| Stuck on "Verifying..." | Large artifact, slow hash | Wait, check disk speed, verify manually |
| Rollback failed | Corrupted backup, no snapshot | Manual reinstall, contact support |
| "Channel not found" | Typo in channel name | Check spelling: stable/beta/alpha/nightly/dev/enterprise |

---

## Common Issues by Category

### Update Check Issues

#### "No update available" but I know there's a new version

**Possible causes:**
1. **Wrong channel** - You're on `stable` but update is in `beta`
2. **Rollout percentage** - Update at 5%, you're not in the 5%
3. **Cache** - Old manifest cached
4. **Version comparison** - You're already on that version

**Solutions:**
```bash
# Check current channel
aetheros config get autoUpdate.channel

# Switch channel if needed
aetheros config set autoUpdate.channel beta

# Force check (bypass cache)
aetheros update check --force

# Check current version
aetheros --version
```

#### Update check fails with network error

**Possible causes:**
1. No internet connection
2. Firewall/proxy blocking
3. Update server down
4. TLS certificate issue

**Solutions:**
```bash
# Test connectivity
curl -I https://updates.aetheros.com/api/v1/health

# Check proxy settings
aetheros config get network.proxy

# Check system time (TLS needs correct time)
date

# Try with verbose logging
AETHEROS_LOG_LEVEL=debug aetheros update check
```

### Download Issues

#### Download fails or stalls

**Possible causes:**
1. Unstable network
2. CDN issue
3. Disk full
4. Antivirus blocking

**Solutions:**
```bash
# Check disk space
df -h  # Linux/macOS
dir    # Windows (check free space)

# Check download cache
ls -la ~/.cache/aetheros/downloads/  # Linux/macOS
dir %LOCALAPPDATA%\AetherOS\downloads\  # Windows

# Clear download cache
rm -rf ~/.cache/aetheros/downloads/*  # Linux/macOS
del /q %LOCALAPPDATA%\AetherOS\downloads\*  # Windows

# Retry with verbose
AETHEROS_LOG_LEVEL=debug aetheros update download
```

#### Download completes but verification fails

**Possible causes:**
1. Corrupted download
2. CDN serving wrong file
3. Manifest hash incorrect
4. Disk corruption

**Solutions:**
```bash
# Clear and re-download
aetheros update download --force

# Manual hash verification
sha256sum /path/to/downloaded/artifact
# Compare with manifest hash

# Check artifact size
ls -lh /path/to/artifact
```

### Installation Issues

#### "Permission denied" / UAC / sudo issues

**Windows:**
```cmd
# Run as Administrator
# Right-click AetherOS → "Run as administrator"

# Check UAC settings
Control Panel → User Accounts → Change UAC settings
# Should not be "Never notify"

# Check if installed per-machine
wmic product where "name like 'AetherOS%'" get InstallLocation
```

**macOS:**
```bash
# Check if app is in Applications
ls -la /Applications/AetherOS.app

# Check Gatekeeper
spctl --assess --type execute /Applications/AetherOS.app

# Reset quarantine if needed
xattr -cr /Applications/AetherOS.app
```

**Linux:**
```bash
# Check sudo access
sudo -v

# Check if in sudoers
sudo -l

# For AppImage, check executable bit
chmod +x AetherOS-*.AppImage

# For DEB/RPM, use package manager
sudo apt install ./aetheros_*.deb
sudo dnf install ./aetheros-*.rpm
```

#### Installer fails with error code

**Windows (NSIS/MSI):**
| Code | Meaning | Action |
|------|---------|--------|
| 1603 | Fatal error | Check Windows Installer logs: `%TEMP%\MSI*.log` |
| 1618 | Another install running | Wait for other install to finish |
| 1619 | Package not found | Verify MSI path |
| 1625 | Install forbidden by policy | Check Group Policy |

**macOS (PKG/DMG):**
```bash
# Check installer log
/var/log/install.log

# Verify package signature
pkgutil --check-signature /path/to/installer.pkg

# Check Gatekeeper
spctl --assess --type install /path/to/installer.pkg
```

**Linux (DEB/RPM):**
```bash
# DEB
sudo dpkg -i package.deb
# Check: dpkg -l | grep aetheros

# RPM
sudo dnf install package.rpm
# Check: rpm -q aetheros

# Flatpak
flatpak install --system flathub com.aetheros.AetherOS
flatpak update com.aetheros.AetherOS
```

### Post-Install Issues

#### App won't launch after update

**Symptoms:**
- Click icon, nothing happens
- Process starts then exits immediately
- Error dialog on launch

**Diagnosis:**
```bash
# Check logs
# Windows: %APPDATA%\AetherOS\logs\errors.log
# macOS: ~/Library/Logs/AetherOS/errors.log
# Linux: ~/.local/share/aetheros/logs/errors.log

# Run from terminal to see output
# Windows: "%APPDATA%\AetherOS\AetherOS.exe"
# macOS: /Applications/AetherOS.app/Contents/MacOS/AetherOS
# Linux: ./AetherOS.AppImage or /opt/aetheros/aetheros
```

**Common causes & fixes:**
1. **Health check failed** - Auto-rollback should have occurred. Check if rollback happened.
2. **Missing dependency** - Run dependency check: `ldd` (Linux), `otool -L` (macOS)
3. **Config migration failed** - Reset config: `aetheros config reset`
4. **Corrupted update** - Manual rollback: `aetheros update rollback`

#### App launches but features broken

**Symptoms:**
- UI loads but commands fail
- IPC errors in console
- Backend connection fails

**Diagnosis:**
```bash
# Check IPC
# Open DevTools (Ctrl+Shift+I) → Console
# Look for: "aetheros:ipc:" messages

# Check backend connection
curl http://localhost:PORT/health

# Check config
aetheros config show
```

### Rollback Issues

#### Automatic rollback didn't happen

**Possible causes:**
1. Health checks not configured
2. Crash loop detection disabled
3. No snapshot available

**Manual rollback:**
```bash
# Check rollback availability
aetheros update rollback-info

# Manual rollback
aetheros update rollback

# If that fails, manual reinstall previous version
# Download previous version from: https://releases.aetheros.com/
```

#### Rollback failed

**Symptoms:**
- "Rollback failed" error
- App in broken state
- User data concerns

**Recovery steps:**
```bash
# 1. Export user data first
aetheros export --output ~/aetheros-backup.json

# 2. Clean uninstall
# Windows: Control Panel → Uninstall
# macOS: rm -rf /Applications/AetherOS.app ~/Library/Application\ Support/AetherOS
# Linux: sudo apt remove aetheros / flatpak uninstall com.aetheros.AetherOS

# 3. Clean install previous version
# Download from: https://releases.aetheros.com/previous/

# 4. Import user data
aetheros import --input ~/aetheros-backup.json
```

### Channel & Rollout Issues

#### Stuck on old version despite new release

**Check:**
```bash
# Current channel
aetheros config get autoUpdate.channel

# Force check
aetheros update check --force

# Check rollout status
curl https://updates.aetheros.com/api/v1/releases/latest/status
```

**Common issues:**
1. **Channel mismatch** - You're on `stable`, release is in `beta`
2. **Rollout percentage** - You're not in the rollout cohort
3. **Prerelease disabled** - Release is alpha/beta, `allowPrerelease: false`
4. **Cache** - Old manifest cached

### Security Errors

#### "Signature verification failed"

**Immediate actions:**
1. **Do not bypass** - This indicates potential compromise
2. **Clear download cache** and re-download
3. **Check system time** - TLS/cert validation needs correct time
5. **Contact support** if persists

```bash
# Force clean re-download
rm -rf ~/.cache/aetheros/downloads/*
aetheros update check --force
aetheros update download
```

#### "Certificate expired" / TLS errors

**Check system time:**
```bash
# Linux/macOS
date
sudo ntpdate -s time.nist.gov  # or use timedatectl

# Windows
w32tm /resync
```

**Check certificate:**
```bash
openssl s_client -connect updates.aetheros.com:443 -servername updates.aetheros.com </dev/null
```

### Network & Proxy Issues

#### Corporate proxy

```bash
# Configure proxy
aetheros config set network.proxy "http://proxy.company.com:8080"

# Or use environment variables
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080
export NO_PROXY=localhost,127.0.0.1,.local
```

#### Firewall blocking

**Required outbound:**
- `updates.aetheros.com:443` (manifest + artifacts)
- `releases.aetheros.com:443` (artifact CDN)
- `telemetry.aetheros.com:443` (optional, if enabled)

**Test:**
```bash
# Test connectivity
nc -zv updates.aetheros.com 443
nc -zv releases.aetheros.com 443

# Or with curl
curl -v https://updates.aetheros.com/api/v1/health
```

### Log Analysis

#### Finding relevant logs

**Windows:**
```
%APPDATA%\AetherOS\logs\
  agent.log      - General agent logs
  errors.log     - Errors and warnings
  gateway.log    - Gateway logs (if running)
```

**macOS:**
```
~/Library/Logs/AetherOS/
  agent.log
  errors.log
```

**Linux:**
```
~/.local/share/aetheros/logs/
  agent.log
  errors.log
```

**Update-specific logs:**
```
# Search for update-related entries
grep -i "update" ~/.local/share/aetheros/logs/agent.log
grep -i "rollback\|health.check" ~/.local/share/aetheros/logs/errors.log
```

#### Log levels

```bash
# Set log level temporarily
AETHEROS_LOG_LEVEL=debug aetheros update check

# Or permanently
aetheros config set logging.level debug
```

#### Key log patterns

| Pattern | Meaning |
|---------|---------|
| `[updates] check started` | Update check initiated |
| `[updates] manifest fetched` | Manifest downloaded |
| `[updates] verification passed` | Signature/hash OK |
| `[updates] download started` | Artifact download begun |
| `[updates] verification failed` | **SECURITY ISSUE** |
| `[updates] rollback initiated` | Automatic rollback |
| `[updates] health check failed` | Post-install validation failed |
| `[updates] kill switch active` | Release killed by server |

---

## Diagnostic Commands

### Quick Health Check
```bash
# Full diagnostic
aetheros doctor

# Or manually:
aetheros --version
aetheros config show
aetheros update check --force
aetheros update rollback-info
```

### Export Debug Info
```bash
# Create support bundle
aetheros debug bundle --output ~/aetheros-debug.zip

# Contents:
# - System info
# - Config (sanitized)
# - Recent logs
# - Update history
# - Config hashes
```

### Manual Verification
```bash
# Verify current install
aetheros verify-install

# Check update config
cat ~/.config/aetheros/updates.json  # Linux/macOS
type %APPDATA%\AetherOS\updates.json  # Windows

# Check update cache
ls -la ~/.cache/aetheros/
```

---

## When to Contact Support

**Contact support if:**
- Multiple failed installs/rollbacks
- Suspected security incident
- Data loss after update
- Persistent crash loops
- Enterprise deployment issues

**Include in support request:**
1. `aetheros doctor` output
2. `aetheros debug bundle` output
3. Steps to reproduce
4. Expected vs actual behavior
5. Screenshots of errors

---

## Prevention

### Best Practices
1. **Keep auto-update enabled** - Security updates applied automatically
2. **Use stable channel** - Unless you need beta features
3. **Monitor disk space** - Keep >2GB free for updates
4. **Regular backups** - `aetheros export` weekly
5. **Check logs periodically** - Catch issues early

### Enterprise
- Test updates in staging channel first
- Use Group Policy/MDM to manage config
- Schedule updates during maintenance windows
- Monitor rollout metrics via admin dashboard