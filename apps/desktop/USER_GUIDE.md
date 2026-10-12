# AetherOS Desktop User Guide

## Overview
AetherOS Desktop is the client application for the AetherOS platform — a universal AI agent operating system. This guide covers everyday usage for end users.

## Getting Started

### First Launch
1. **Welcome Screen:** Choose your language and theme preference
2. **Sign In:** Authenticate with your AetherOS account
3. **Workspace Setup:** Configure your default workspace directory
4. **Onboarding Tour:** Quick overview of key features

### Dashboard
The dashboard is your home screen, showing:
- Recent activity
- Connected agents and services
- System status overview
- Quick actions

## Core Features

### Agent Management
- **View Agents:** All active and available agents listed on the dashboard
- **Launch Agent:** Click an agent card or use the command palette (Ctrl+P)
- **Configure Agent:** Agent-specific settings via the configuration panel
- **Monitor Agent:** Real-time activity feed and performance metrics

### Workspace
- **Create Workspace:** File → New Workspace or click "+" in workspace panel
- **Open Workspace:** File → Open Workspace or Recent Workspaces list
- **Manage Files:** Built-in file browser with drag-and-drop support
- **Workspace Settings:** Per-workspace configuration (language, environment, etc.)

### Resource Manager (Ctrl+R)
Monitor and manage system resources:
- **CPU:** Per-core utilization and process breakdown
- **Memory:** RAM usage by application and process
- **Storage:** Disk usage with cleanup recommendations
- **Network:** Bandwidth usage and active connections
- **GPU:** Graphics memory and utilization metrics

### Diagnostics Center (Ctrl+D)
Comprehensive system diagnostics:
- **System Info:** OS version, hardware specs, runtime details
- **Performance Metrics:** Real-time charts for resource usage
- **Logs:** Application logs with severity filtering and export
- **Health Checks:** Automated verification of all system components
- **Telemetry:** Anonymous usage statistics (opt-in)

### Service Manager (Ctrl+S)
Manage background services:
- **Services List:** All registered services with status indicators
- **Start/Stop/Restart:** Per-service lifecycle control
- **Service Logs:** Per-service log viewer with filtering
- **Dependencies:** Visual dependency graph between services
- **Auto-start Configuration:** Configure which services start on launch

### Secure Sandbox (Ctrl+Shift+S)
Manage sandboxed environments:
- **Create Sandbox:** Configure isolated runtime environment
- **Resource Limits:** CPU/RAM/network restrictions per sandbox
- **Permissions:** Granular permission control
- **Sandbox Monitor:** Real-time resource usage per sandbox
- **Export/Import:** Package and share sandbox configurations

### Command Palette (Ctrl+P)
Quick access to all features:
- Type to search commands, settings, and files
- Use `>` prefix for commands
- Use `#` for workspace files
- Use `:` for line navigation

### Notifications
- Bell icon in title bar shows unread count
- Click to open notification center
- Configure notification preferences in Settings

## Settings

### General
- **Language:** Interface language selection
- **Theme:** Light, Dark, or System (auto)
- **Font Size:** Small, Medium, Large, Extra Large
- **Reduced Motion:** Disable animations for accessibility
- **High Contrast:** Enhanced contrast mode

### Account
- **Profile:** View and edit profile information
- **Preferences:** Agent behavior defaults
- **Security:** Password, 2FA, session management
- **API Keys:** Manage API keys for external integrations

### Workspace
- **Default Directory:** Default workspace location
- **Auto-save:** Enable/disable auto-save with interval
- **File Associations:** Default file handlers

### Agents
- **Default Agent:** Which agent to activate on launch
- **Agent Timeout:** Maximum wait time for agent responses
- **Resource Limits:** Per-agent CPU/RAM limits

### Privacy
- **Telemetry:** Enable/disable anonymous usage data
- **Crash Reports:** Enable/disable automatic crash reporting
- **Data Collection:** Configure what data is collected

### Updates
- **Channel:** Stable, Beta, or Nightly
- **Auto-update:** Enable/disable automatic updates
- **Check Now:** Manually check for updates

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+P | Command Palette |
| Ctrl+R | Resource Manager |
| Ctrl+D | Diagnostics Center |
| Ctrl+S | Service Manager |
| Ctrl+Shift+S | Secure Sandbox |
| Ctrl+, | Settings |
| Ctrl+Shift+E | Workspace Explorer |
| Ctrl+Shift+P | Agent Launcher |
| F11 | Toggle Fullscreen |
| Ctrl+W | Close Tab |

## Accessibility

### Available Features
- **Screen Reader Support:** ARIA labels and landmarks throughout
- **Keyboard Navigation:** Full keyboard accessibility (Tab, Enter, Escape)
- **High Contrast:** Enhanced contrast theme for readability
- **Reduced Motion:** Disable animations
- **Font Scaling:** Adjustable font sizes
- **Focus Indicators:** Visible focus outlines

### Activation
- Settings → General → Accessibility Options
- Or use the accessibility quick toggle (Ctrl+Shift+A)

## Troubleshooting

### Common Issues

**App won't start:**
1. Check system requirements
2. Run with `--safe-mode` flag
3. Reset configuration: `--reset-config`
4. Reinstall if necessary

**Agent not responding:**
1. Check agent status in Service Manager (Ctrl+S)
2. Restart the agent service
3. Check logs in Diagnostics Center (Ctrl+D)
4. Verify network connectivity

**High memory usage:**
1. Open Resource Manager (Ctrl+R)
2. Identify memory-heavy components
3. Restart services or sandboxes as needed
4. Consider increasing system RAM

**Updates not installing:**
1. Check internet connectivity
2. Verify update channel in Settings
3. Manual download from releases page
4. Check disk space

### Crash Recovery
If the app crashes:
1. **Automatic Recovery:** The app will attempt to restart automatically
2. **Safe Mode:** If crashes persist, run with `--safe-mode` to disable extensions
3. **Crash Reports:** Crash reports are saved to the diagnostics directory
4. **Reset:** Use `--reset-config` if configuration corruption is suspected

### Logs
- Application logs: `~/.config/aetheros/logs/`
- Crash reports: `~/.config/aetheros/crashes/`
- Diagnostics export: File → Export Diagnostics

## Support
- **Documentation:** https://aetheros.dev/docs
- **GitHub Issues:** https://github.com/aetheros/aetheros/issues
- **Discord Community:** https://discord.gg/aetheros
- **Email:** support@aetheros.dev
