# AetherOS Desktop

Production-ready desktop client for the AetherOS platform — a universal AI agent operating system.

## Features

- **Multi-platform:** Windows, macOS, Linux (x64 + ARM64)
- **Secure:** Sandboxed renderer, encrypted storage, context isolation
- **Enterprise-ready:** Code signing, auto-updates, crash recovery
- **Internationalized:** English, Japanese, Korean, Chinese (Traditional)
- **Accessible:** WCAG 2.1 AA target, keyboard navigation, screen reader support
- **Extensible:** Plugin system with sandboxed runtime

## Quick Start

```bash
# Install dependencies
npm ci

# Development
npm run dev

# Build & package for current platform
npm run dist

# Run tests
npm run test:ui
```

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS | Windows 10 / macOS 12 / Ubuntu 22.04 | Windows 11 / macOS 14 / Ubuntu 24.04 |
| CPU | 2 cores, 64-bit | 4+ cores |
| RAM | 4 GB | 8 GB+ |
| Storage | 500 MB | 2 GB+ |
| GPU | DirectX 12 / Metal / Vulkan | Dedicated GPU |

## Documentation

| Document | Description |
|----------|-------------|
| [INSTALL.md](INSTALL.md) | Installation guide for all platforms |
| [USER_GUIDE.md](USER_GUIDE.md) | End-user documentation |
| [ADMIN_GUIDE.md](ADMIN_GUIDE.md) | Administrator deployment guide |
| [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) | Developer setup and contribution |
| [API_REFERENCE.md](API_REFERENCE.md) | Preload bridge API reference |
| [SECURITY.md](SECURITY.md) | Security policies and audit report |
| [PRIVACY.md](PRIVACY.md) | Privacy policy and data handling |
| [ROADMAP.md](ROADMAP.md) | Development roadmap |
| [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) | Release preparation checklist |
| [CHANGELOG.md](CHANGELOG.md) | Version history |

## Build Targets

### Distributions
- **macOS:** DMG, ZIP (Intel + Apple Silicon)
- **Windows:** NSIS installer, MSI
- **Linux:** AppImage, deb, rpm

### Code Signing
- **macOS:** Apple notarization via `notarize.cjs`
- **Windows:** Authenticode signing via `afterPack` hook
- **Linux:** GPG signature for deb/rpm packages

## CI/CD

| Workflow | Status | Schedule |
|----------|--------|----------|
| Build | Push/PR on main | On demand |
| Release | Tag push (v*) | Manual trigger |
| Nightly | Daily 06:00 UTC | Automatic |
| Tests | Push/PR on main | On demand |
| Security | Weekly on Monday | Automatic |

## Project Structure

```
apps/desktop/
├── electron/          # Electron main process & preload
│   ├── main.cjs       # Main process (8400+ lines)
│   ├── preload.cjs    # Preload bridge (~56 exports)
│   └── *.test.cjs     # Electron module tests
├── src/               # React renderer
│   ├── components/    # UI components (shadcn/ui + Tailwind v4)
│   ├── store/         # Nanostores state management
│   ├── i18n/          # Localization
│   └── lib/           # Utilities (crash recovery, services, etc.)
├── build/             # Build config (entitlements, code signing)
├── scripts/           # Development and CI scripts
│   ├── release/       # Release engineering
│   ├── security/      # Security auditing
│   └── quality/       # Quality verification
├── docs/              # Production documentation
└── package.json
```

## Tech Stack

- **Runtime:** Electron 40.9.3 + Node ^20.19.0 || >=22.12.0
- **UI:** React 19 + TypeScript 5.8 + Tailwind CSS v4
- **State:** Nanostores + React integration
- **Build:** Vite 8 + electron-builder
- **Packaging:** electron-builder (NSIS, MSI, DMG, AppImage, deb, rpm)
- **Testing:** Vitest, Node Test Runner, Playwright
- **Linting:** ESLint + Prettier

## Security

- Context isolation enabled; node integration disabled
- Renderer sandbox enabled
- IPC channel allowlisting and path validation
- Encrypted token storage using OS keychain
- CSP headers configured
- Crash loop breaker with safe mode entry
- Code signing: macOS notarization, Windows Authenticode

## License

[License information]
