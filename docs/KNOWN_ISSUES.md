# AetherOS — Known Issues

**Generated:** July 14, 2026

---

## Critical Issues

| ID | Issue | Impact | Workaround | Fixed In |
|----|-------|--------|------------|----------|
| C001 | Dashboard auth confidential client OAuth not implemented | Self-hosted deployments cannot use OAuth flow | Use API key auth only | Pending |
| C002 | Dashboard chat embedded TUI uses POSIX PTY — no native Windows support | Windows users cannot use embedded chat in dashboard | Use WSL or native CLI/TUI | Pending |
| C003 | Desktop app has incomplete feature parity with CLI/TUI | Some features only available via CLI | Use CLI for missing features | Pending |

---

## Medium Issues

| ID | Issue | Impact | Workaround | Fixed In |
|----|-------|--------|------------|----------|
| M001 | `run_agent.py` is ~12,000 lines | Maintainability, difficult to navigate | — | Ongoing refactor |
| M002 | `cli.py` is ~11,000 lines | Maintainability, difficult to navigate | — | Ongoing refactor |
| M003 | Dashboard analytics page hidden behind feature flag | Users cannot see token analytics | Set `show_token_analytics: true` in config | Pending |
| M004 | Kanban per-board dispatcher tracking not implemented | Limited multi-tenant visibility | — | Pending |
| M005 | Yuanbao chat metadata (name, member count) not fetched | Incomplete platform integration | — | Pending |
| M006 | TUI markdown-to-ANSI has rendering gaps | Some markdown renders poorly | Use CLI or desktop for markdown-heavy sessions | Pending |
| M007 | TUI Ink screen lacks soft-wrapping for spacer cells | Layout glitches in certain terminal sizes | Resize terminal | Pending |
| M008 | Desktop tests only cover electron main process (16 files) | Renderer has zero test coverage | Manual testing | Pending |
| M009 | Web dashboard tests largely absent | UI regressions possible | Manual testing | Pending |

---

## Minor Issues

| ID | Issue | Impact | Workaround |
|----|-------|--------|------------|
| L001 | Some `HERMES_*` env vars still referenced | Rebranding incomplete | Use both old and new names |
| L002 | Legacy `hermes` entry point may still exist | Dual naming confusion | Use `aetheros` command |
| L003 | Yuanbao adapter is very large (4.8K LOC) | Maintainability | — |
| L004 | Some gateway adapters may lack full test coverage | Possible edge-case bugs | Report if found |
| L005 | Optional skills templates have placeholder TODOs | Template customization needed | Fill in custom problem definitions |

---

## Platform-Specific Issues

### Windows
- Dashboard chat PTY doesn't work natively (WSL required)
- Some shell hooks use POSIX-only primitives
- Terminal backend tests limited

### macOS
- Notarization required for distribution
- Some entitlements may need updating for new APIs

### Linux
- AppImage/Flatpak/Snap not yet available (only deb/rpm)
- Some distros may need additional system packages

### Termux (Android)
- Limited to CLI mode
- Some optional deps unavailable on ARM

---

## Deprecated Features

| Feature | Deprecation Version | Replacement | Notes |
|---------|---------------------|-------------|-------|
| `MESSAGING_CWD` env var | 0.16.0 | `terminal.cwd` in config.yaml | Prints deprecation warning |
| `TERMINAL_CWD` in `.env` | 0.16.0 | `terminal.cwd` in config.yaml | Config is canonical |
| Legacy `providers/<name>.py` | 0.16.0 | `plugins/model-providers/<name>/` | Back-compat maintained |
| `hermes` CLI command name | Rebranded | `aetheros` | Both work |
| In-tree memory provider additions | Policy (May 2026) | External plugin repos | No new in-tree providers |
| `terminal` as env_type | 0.16.0 | `backend` key | Both work, `backend` preferred |

---

## Security Advisories

| Advisory | Component | Status | Fix Version |
|----------|-----------|--------|-------------|
| CVE-2026-34450, CVE-2026-34452 | anthropic | Patched | 0.87.0 |
| CVE-2026-48710 (BadHost) | starlette | Patched | 1.0.1 |
| CVE-2026-34513/34518/34519/34520/34525 | aiohttp | Patched | 3.13.4 |
| CVE-2026-25645 | requests | Patched | 2.33.0 |
| GHSA-mf9v-mfxr-j63j | urllib3 | Patched | 2.7.0 |
| GHSA-qccp-gfcp-xxvc | urllib3 | Patched | 2.7.0 |
| PYSEC-2026-175/177/178/179 | PyJWT | Patched | 2.13.0 |

---

## How to Report Issues

- **Bug reports:** GitHub Issues
- **Security vulnerabilities:** GitHub Security Advisories or security@aetheros.com
- **Feature requests:** GitHub Discussions or Issues

See SECURITY.md for full disclosure policy (90-day coordinated disclosure window).
