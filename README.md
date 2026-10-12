# AetherOS

[![GitHub Stars](https://img.shields.io/github/stars/mdsabibahamedsad/AetherOS?style=social)](https://github.com/mdsabibahamedsad/AetherOS/stargazers)
![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)

AetherOS is a personal AI operating environment — one assistant that runs
across an Electron desktop app, a terminal UI, a CLI, and a messaging gateway
(Telegram, Discord, Slack, and more). It learns across sessions (memory +
skills), delegates to subagents, runs scheduled jobs, and drives a real
terminal and browser.

> Tell AetherOS what you want accomplished. Your AI assistant handles the work.

## Highlights

- **One agent core, many surfaces** — desktop (`apps/desktop`), terminal UI
  (`ui-tui`), CLI (`cli.py`), and messaging gateway (`gateway/`) share the
  same runtime (`run_agent.py`).
- **Command center desktop** — Home composer, Chat with streaming + tool
  cards, Jarvis voice/text mode, Tasks, Agents, Models, Memory, Knowledge,
  Files, Browser, Automation, Security Center, diagnostics, and settings.
- **Real tool execution** — auto-discovered tool registry with per-platform
  toolsets, MCP server catalog, approvals for sensitive actions, and
  cancellation that is never mislabeled as success.
- **Memory & skills** — pluggable memory providers, bundled + optional
  skills, and background skill curation with archives instead of deletes.
- **Delegation** — `delegate_task` spawns isolated subagents (single or
  parallel) with bounded depth and concurrency.
- **Automation** — cron-style scheduled jobs with retries, catchup windows,
  and per-job model/skill overrides.
- **Security by design** — Electron context isolation, narrow preload APIs,
  prompt-injection scanners on memory/cron/browser/network paths, untrusted
  tool-output delimiters, and a permission/approval policy enforced across
  every entry point.

## Quickstart

### Desktop app (Windows/macOS/Linux)

```bash
cd aetheros/apps/desktop
npm install
npm run dev        # renderer + Electron (dev server on 127.0.0.1:5174)
```

Useful scripts: `npm run typecheck`, `npm run test:ui`, `npm run lint`,
`npm run build` (requires a git checkout for the build stamp).

### CLI / TUI (Python)

```bash
cd aetheros
source .venv/bin/activate   # or: source venv/bin/activate
python run_agent.py --help
aetheros --tui              # full terminal UI
```

Run tests the CI-parity way (never plain `pytest`):

```bash
scripts/run_tests.sh
```

### Configuration

- Settings live in `~/.aetheros/config.yaml`; **secrets only** in `~/.aetheros/.env`
  (API keys, tokens, passwords). Non-secret settings belong in `config.yaml`.
- Multiple isolated instances via profiles (`aetheros -p <name>`), each with
  its own `AETHEROS_HOME`.

## Repository layout

```
aetheros/
├── apps/desktop/     # Electron + React + nanostore desktop shell
├── ui-tui/           # Ink terminal UI (aetheros --tui)
├── tui_gateway/      # JSON-RPC backend for the TUI/desktop chat
├── gateway/          # Messaging gateway + platform adapters
├── tools/            # Auto-discovered tool implementations
├── skills/           # Built-in skills (optional-skills/ for niche ones)
├── plugins/          # Plugin surfaces (memory, model-providers, …)
├── cron/             # Scheduler (jobs + tick loop)
├── agent/            # Agent internals (providers, memory, compression)
├── aetheros_cli/     # CLI subcommands, setup, skins
├── website/          # Docusaurus docs site
├── tests/            # Pytest suite (run via scripts/run_tests.sh)
└── docs/             # Architecture, audit, and acceptance reports
```

## Extending (no core changes needed)

- **New capability?** Prefer: extend existing code → CLI command + skill →
  service-gated tool → plugin → MCP catalog entry → new core tool (last resort).
- **New tool:** create `tools/<name>.py` with `registry.register(...)`, then
  wire it into a toolset in `toolsets.py`.
- **New slash command:** add a `CommandDef` in `aetheros_cli/commands.py`.
- **Custom tools:** use user plugins (`~/.aetheros/plugins/`) — plugins must
  not modify core files.

See `aetheros/AGENTS.md` for the full contributor guide and
`aetheros/docs/` for architecture and acceptance evidence.

## Status & honesty rules

- This repo publishes code, not completion claims. Live model, voice, and
  packaged-installer validation each require credentials/hardware/provenance
  documented in `docs/`.
- Stars, issues, and PRs are welcome — please include reproduction steps and
  exact failing lines for bug reports.

## License

MIT — see [LICENSE](LICENSE).
