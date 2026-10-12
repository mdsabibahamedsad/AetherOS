# AetherOS Desktop Developer Guide

## Setup

### Prerequisites
- Node.js ^20.19.0 || >=22.12.0
- npm 10+
- Git
- Platform-specific build tools:
  - **Windows:** Visual Studio 2022 Build Tools, Windows SDK
  - **macOS:** Xcode 15+ Command Line Tools
  - **Linux:** `build-essential`, `libgtk-3-dev`, `libwebkit2gtk-4.1-dev`

### Clone & Install
```bash
git clone https://github.com/aetheros/aetheros.git
cd aetheros
npm ci
cd apps/desktop
npm ci
```

### Platform-Specific Setup

#### Windows
```powershell
# Install Visual Studio Build Tools (required for native modules)
# Download from: https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022
# Select: "Desktop development with C++"

# Verify
npm run build
```

#### macOS
```bash
# Install Xcode Command Line Tools
xcode-select --install

# Verify
npm run build
```

#### Linux
```bash
# Ubuntu/Debian
sudo apt-get install -y libgtk-3-dev libwebkit2gtk-4.1-dev libappindicator3-dev librsvg2-dev patchelf

# Fedora
sudo dnf install gtk3-devel webkit2gtk4.1-devel libappindicator-gtk3-devel librsvg2-devel

# Arch
sudo pacman -S gtk3 webkit2gtk-4.1 libappindicator-gtk3 librsvg patchelf
```

## Development

### Start Dev Server
```bash
npm run dev
```
This starts the Vite dev server and launches Electron with hot-reload.

### Project Structure
```
apps/desktop/
├── electron/
│   ├── main.cjs          # Electron main process
│   ├── preload.cjs       # Preload bridge (contextBridge API)
│   └── *.test.cjs        # Node test runner tests
├── src/
│   ├── components/       # React components (shadcn/ui)
│   │   ├── ui/           # Base UI primitives
│   │   └── features/     # Feature-specific components
│   ├── store/            # Nanostores state managers
│   ├── i18n/             # Localization (JSON)
│   ├── lib/              # Utilities
│   └── App.tsx           # Root component
├── build/                # electron-builder config
├── docs/                 # Production documentation
├── scripts/              # Build/test/release scripts
│   ├── release/          # Release engineering
│   ├── security/         # Security auditing
│   └── quality/          # Quality verification
└── package.json
```

### Key Commands

| Command | Description |
|---------|-------------|
| `npm run dev` | Start dev server with hot-reload |
| `npm run build` | Build renderer for production |
| `npm run dist` | Package for current platform |
| `npm run dist:mac` | Package for macOS |
| `npm run dist:win` | Package for Windows |
| `npm run dist:linux` | Package for Linux |
| `npm run lint` | Lint all source files |
| `npm run typecheck` | TypeScript type checking |
| `npm run test:ui` | Run Vitest unit tests |
| `npm run test:desktop` | Full desktop test suite |
| `node --test electron/*.test.cjs` | Run Electron tests |

### Building for Distribution

```bash
# Development build (quick, no code signing)
npm run build
npx electron-builder --config electron-builder.yml --dir

# Production build (signed, full package)
npm run dist

# Platform-specific
npm run dist:mac    # macOS DMG + ZIP
npm run dist:win    # Windows NSIS + MSI
npm run dist:linux  # Linux AppImage + deb + rpm
```

## Architecture

### Process Model
```
┌─────────────────────────────────────┐
│         Main Process (Node.js)       │
│  ┌────────────────────────────────┐  │
│  │  IPC Handler (allowlist)      │  │
│  │  Window Manager               │  │
│  │  Auto-updater                 │  │
│  │  Native Dialogs               │  │
│  │  File System Access           │  │
│  └────────────────────────────────┘  │
└────────────────┬────────────────────┘
                 │ IPC (contextBridge)
┌────────────────▼────────────────────┐
│       Renderer Process (Chromium)    │
│  ┌────────────────────────────────┐  │
│  │  React App (Vite)             │  │
│  │  Nanostores (State)           │  │
│  │  shadcn/ui (Components)       │  │
│  │  Tailwind CSS v4 (Styling)    │  │
│  └────────────────────────────────┘  │
└─────────────────────────────────────┘
```

### IPC Communication
- All IPC uses `contextBridge.exposeInMainWorld` in preload
- Channels are validated against an allowlist
- Path arguments are sanitized
- No `nodeIntegration` — security by isolation

### State Management
- **Nanostores** for reactive state
- **Atom pattern** for fine-grained updates
- **Maps/async stores** for collections
- Stores are scoped to features/libraries

### Adding a New Store
```typescript
import { atom, map } from 'nanostores';

// Simple value
export const $count = atom(0);

// Collection
export const $items = map<Record<string, Item>>({});

// Actions
export function increment() {
  $count.set($count.get() + 1);
}
```

### Adding a New Component
1. Create in `src/components/features/` or `src/components/ui/`
2. Import shadcn/ui primitives from `src/components/ui/`
3. Use Tailwind v4 utility classes
4. Add ARIA labels for accessibility
5. Add nanostores integration if needed

## Testing

### Unit Tests (Vitest)
```bash
npm run test:ui
npm run test:ui -- --coverage  # With coverage
```

### Electron Module Tests
```bash
node --test electron/*.test.cjs
```

### Integration Tests
```bash
npm run test:desktop:all
```

### Adding Tests
```typescript
// src/store/example.test.ts
import { expect, test } from 'vitest';

test('store increments correctly', () => {
  // Test logic
});
```

## Internationalization (i18n)

### Adding a New Locale
1. Create `src/i18n/{locale}.json`
2. Copy all keys from `en.json`
3. Translate values
4. Register in the i18n configuration

### Adding New Translation Keys
1. Add key to `src/i18n/en.json`
2. Add translations to other locale files
3. Access in code: `import { t } from 'src/i18n'`

## Security Guidelines

### IPC Security
- All channels must be in the allowlist
- Validate all path arguments
- Never expose Node.js APIs directly
- Use contextBridge only

### Main Process Security
- Disable nodeIntegration in renderer
- Enable sandbox
- Set CSP headers
- Validate all file operations

### Renderer Security
- No direct filesystem access
- All external communication via IPC
- Content Security Policy enforced

## Performance

### Build Optimization
- Use `npm run build` for production bundles
- Vite handles code splitting and tree shaking
- Enable source maps only in development

### Runtime Optimization
- Lazy load infrequently used components
- Virtualize large lists
- Use nanostores for targeted re-renders
- Profile with Chrome DevTools

## Debugging

### VSCode Launch Config
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Debug Main Process",
      "type": "node",
      "request": "launch",
      "cwd": "${workspaceFolder}/apps/desktop",
      "runtimeExecutable": "npm",
      "runtimeArgs": ["run", "dev"],
      "env": { "NODE_ENV": "development" }
    },
    {
      "name": "Debug Renderer",
      "type": "chrome",
      "request": "attach",
      "port": 9222,
      "webRoot": "${workspaceFolder}/apps/desktop/src"
    }
  ]
}
```

### Logging
```typescript
// Main process
import { log } from 'electron-log';

// Renderer
console.log('Debug info');  // Appears in DevTools console
```

## Release Process

### Creating a Release
```bash
# 1. Bump version
node scripts/release/bump-version.mjs {major|minor|patch}

# 2. Update CHANGELOG.md

# 3. Generate release notes
VERSION=x.y.z node scripts/release/generate-release-notes.mjs

# 4. Commit and tag
git add -A
git commit -m "Release vx.y.z"
git tag vx.y.z

# 5. Push (triggers CI/CD)
git push && git push --tags
```

### Pre-release Checklist
See [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md).

### CI/CD
- **Build:** Triggered on push/PR to main
- **Release:** Triggered on tag push (v*)
- **Nightly:** Daily at 06:00 UTC
- **Tests:** On every push/PR
- **Security:** Weekly on Monday

## Code Signing

### macOS
- Apple Developer ID certificate required
- Notarization via `build/notarize.cjs`
- Set `APPLE_ID`, `APPLE_APP_SPECIFIC_PASSWORD`, `APPLE_TEAM_ID`

### Windows
- Authenticode certificate (EV or standard)
- Set `CSC_LINK` and `CSC_KEY_PASSWORD` environment variables

### Linux
- GPG key for package signing
- Set `GPG_SIGN_KEY` and `GPG_SIGN_PASSPHRASE`

## Contributing

### Pull Request Process
1. Create a feature branch from `main`
2. Make your changes
3. Run all tests: `npm run test:desktop:all`
4. Run lint: `npm run lint`
5. Update CHANGELOG.md
6. Submit PR with description

### Code Review Checklist
- [ ] TypeScript strict mode passes
- [ ] ESLint no warnings/errors
- [ ] Tests pass and coverage maintained
- [ ] Accessibility (ARIA, keyboard nav) considered
- [ ] i18n strings added for new UI text
- [ ] Security implications reviewed
- [ ] CHANGELOG.md updated
