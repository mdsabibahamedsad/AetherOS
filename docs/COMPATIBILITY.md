# AetherOS — Platform Compatibility

**Generated:** July 14, 2026

---

## Operating Systems

| OS | Status | Notes |
|----|--------|-------|
| **Linux** (x86_64) | ✅ Full | Primary target. All features work. |
| **Linux** (arm64/aarch64) | ✅ Full | Docker, Nix, pip install. |
| **macOS** (Intel) | ✅ Full | Homebrew, DMG, direct install. |
| **macOS** (Apple Silicon) | ✅ Full | Universal binary support planned. |
| **Windows** (x86_64) | ✅ Full | NSIS/MSI installers. Most features work. |
| **Windows** (ARM64) | 🔶 Partial | No native PTY bridge. |
| **Termux** (Android) | ✅ Full | CLI-only, limited to 3.11+ Python. |

---

## Python Versions

| Version | Status | Notes |
|---------|--------|-------|
| 3.11 | ✅ Full | Minimum supported |
| 3.12 | ✅ Full | Actively tested |
| 3.13 | ✅ Full | Primary development version |
| 3.14 | ❌ Unsupported | No Rust wheel support yet (upper bound in pyproject.toml) |

---

## Package Managers

| Manager | Status | Notes |
|---------|--------|-------|
| pip | ✅ Full | PyPI package |
| uv | ✅ Full | Recommended, used in Docker |
| Nix | ✅ Full | flake.nix with packages |
| Homebrew | ✅ Full | macOS formula |
| apt (deb) | ✅ Full | Linux package |
| rpm | ✅ Full | Fedora/RHEL package |
| AppImage | 🔶 Not yet | Planned |
| Flatpak | 🔶 Not yet | Planned |
| Snap | 🔶 Not yet | Planned |
| Chocolatey | 🔶 Not yet | Planned |
| winget | 🔶 Not yet | Planned |

---

## User Interfaces

| Interface | Linux | macOS | Windows | Termux |
|-----------|-------|-------|---------|--------|
| CLI (Rich) | ✅ | ✅ | ✅ | ✅ |
| TUI (Ink) | ✅ | ✅ | ✅ | ✅ |
| Desktop (Electron) | ✅ | ✅ | ✅ | ❌ |
| Web Dashboard | ✅ | ✅ | ✅ | ✅ |
| Gateway (all platforms) | ✅ | ✅ | ✅ | 🔶 Limited |
| Voice (TTS/STT) | ✅ | ✅ | ✅ | ❌ |

---

## Features by Platform

| Feature | Linux | macOS | Windows | Termux |
|---------|-------|-------|---------|--------|
| **Agent Loop** | ✅ | ✅ | ✅ | ✅ |
| **Terminal (local)** | ✅ | ✅ | ✅ | ✅ |
| **Terminal (Docker)** | ✅ | ✅ | ✅ | ❌ |
| **Terminal (SSH)** | ✅ | ✅ | ✅ | ✅ |
| **Terminal (Modal)** | ✅ | ✅ | ✅ | ✅ |
| **Terminal (Daytona)** | ✅ | ✅ | ✅ | ✅ |
| **File Tools** | ✅ | ✅ | ✅ | ✅ |
| **Web Search** | ✅ | ✅ | ✅ | ✅ |
| **Browser** | ✅ | ✅ | ✅ | ❌ |
| **Vision** | ✅ | ✅ | ✅ | ✅ |
| **Code Execution** | ✅ | ✅ | ✅ | ✅ |
| **MCP** | ✅ | ✅ | ✅ | ✅ |
| **All Skills** | ✅ | ✅ | ✅ | 🔶 Platform-gated |
| **All Plugins** | ✅ | ✅ | ✅ | 🔶 Platform-gated |
| **IPC (ACP)** | ✅ | ✅ | ✅ | ❌ |
| **Dashboard Chat (PTY)** | ✅ | ✅ | 🔶 WSL only | ❌ |
| **Gateway (all 16+)** | ✅ | ✅ | ✅ | 🔶 Some missing |
| **Cron** | ✅ | ✅ | ✅ | ✅ |
| **Kanban** | ✅ | ✅ | ✅ | ✅ |
| **Docker Image** | ✅ | ✅ | ❌ | ❌ |
| **Docker Compose** | ✅ | ✅ | ✅ (WSL) | ❌ |
| **Install Script** | ✅ (sh) | ✅ (sh) | ✅ (ps1) | ✅ (sh) |

---

## Browsers (Web Dashboard)

| Browser | Status | Notes |
|---------|--------|-------|
| Chrome | ✅ Full | Primary target |
| Firefox | ✅ Full | Actively tested |
| Safari | ✅ Full | macOS |
| Edge | ✅ Full | Windows |
| Opera | ✅ Full | |
| Brave | ✅ Full | |
| Chromium-based | ✅ Full | All derivatives |

---

## Messaging Platforms

| Platform | Status | Notes |
|----------|--------|-------|
| Telegram | ✅ Full | Bot API |
| Discord | ✅ Full | Bot + Voice |
| Slack | ✅ Full | Bolt framework |
| WhatsApp | ✅ Full | WhatsApp Business |
| Signal | ✅ Full | Signal CLI |
| Email | ✅ Full | IMAP/SMTP |
| SMS | ✅ Full | Twilio |
| Matrix | ✅ Full | Encryption supported |
| Mattermost | ✅ Full | |
| DingTalk | ✅ Full | |
| Feishu/Lark | ✅ Full | |
| WeCom | ✅ Full | |
| Weixin | ✅ Full | |
| QQ Bot | ✅ Full | |
| BlueBubbles | ✅ Full | iMessage bridge |
| Yuanbao | ✅ Full | |
| Home Assistant | ✅ Full | |
| Webhooks | ✅ Full | Generic |
| API Server | ✅ Full | OpenAI-compatible |

---

## Database Support

| Database | Status | Notes |
|----------|--------|-------|
| SQLite (built-in) | ✅ Full | Session storage, cron, kanban |
| ChromaDB | ✅ | Vector store |
| Pinecone | ✅ | Via memory plugins |
| Weaviate | ✅ | Via memory plugins |
| Qdrant | ✅ | Via memory plugins |
| Milvus | ✅ | Via memory plugins |
| PostgreSQL | 🔶 | Via memory plugins |
| Redis | 🔶 | Via memory plugins |

---

## Deployment Environments

| Environment | Status | Notes |
|-------------|--------|-------|
| Bare metal | ✅ | Primary target |
| Docker (single container) | ✅ | s6-overlay |
| Docker Compose | ✅ | Full stack |
| Kubernetes | 🔶 | Partial support |
| NixOS | ✅ | flake.nix |
| macOS Homebrew | ✅ | Formula |
| Windows (direct) | ✅ | Installer |
| Termux | ✅ | CLI-only |
| Cloud VM | ✅ | Any Linux VM |
| Raspberry Pi | ✅ | arm64 Docker |
