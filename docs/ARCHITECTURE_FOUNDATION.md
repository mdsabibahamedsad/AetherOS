# AetherOS Architecture

## Overview

AetherOS is a cross-platform Desktop AI Operating System. It runs the same
agent core across a CLI, a messaging gateway (20+ platforms), a TUI, and an
Electron desktop app.

### Core Design Principle: Narrow Waist

The system is built around a **narrow waist** design — a single `AIAgent`
class powers all interfaces:

```
User Interfaces                  →    Core    →    Tool Implementations
┌──────────────┐                      ┌─┐         ┌──────────────────┐
│ CLI (prompt  │                      │ │         │ Terminal Backends│
│   _toolkit)  │                      │A│         │ File System      │
├──────────────┤                      │I│         │ Web Search       │
│ TUI (Ink)   │  ─── JSON-RPC ────   │A│  ────   │ Browser (CDP)   │
├──────────────┤                      │g│         │ Vision           │
│ Desktop     │                      │e│         │ MCP Servers      │
│  (Electron)  │                      │n│         │ Code Execution   │
├──────────────┤                      │t│         │ Skills/Plugins   │
│ Gateway     │                      │ │         │ Subagents        │
│  (20+       │                      │ │         └──────────────────┘
│   platforms)│                     └─┘
└──────────────┘
```

### Architecture Foundation (`aetheros_arch`)

The `aetheros_arch` package provides the architecture foundation:

| Module | Responsibility |
|--------|---------------|
| `config_manager` | Centralized configuration loading/validation from 7 config files |
| `health_checker` | Component health monitoring and reporting |
| `error_handler` | Structured error handling with user-friendly messages |
| `service_container` | Dependency injection container with lifecycle management |
| `state_manager` | Global application state with persistence and change listeners |
| `boot_sequence` | Deterministic 12-stage boot pipeline |
| `security_foundation` | Encryption, key derivation, and secure secret storage |
| `performance` | Lazy loading, caching, background loading, timing |

## Configuration System

Configuration is managed through 7 JSON files in `~/.aetheros/config/`:

| File | Scope | Content |
|------|-------|---------|
| `config.json` | Core | Version, mode, debug flags |
| `settings.json` | User Preferences | Theme, language, notifications, display |
| `providers.json` | Providers | Default provider/model, per-provider configs |
| `gateway.json` | Gateway | Enabled platforms, ports, host |
| `runtime.json` | Runtime | Max iterations, timeouts, subagent limits |
| `memory.json` | Memory | Enabled, provider, embedding model |
| `security.json` | Security | Encryption, sandbox, permissions, audit |

## Boot Sequence

The boot process follows a strict 12-stage pipeline:

```
Stage 1:  Initialize Logger
Stage 2:  Load Configuration
Stage 3:  Validate Configuration
Stage 4:  Load Providers
Stage 5:  Initialize Gateway
Stage 6:  Initialize Runtime
Stage 7:  Initialize Memory
Stage 8:  Initialize Plugins
Stage 9:  Initialize MCP
Stage 10: Initialize UI
Stage 11: Health Check
Stage 12: Ready
```

Each stage runs synchronously. Pre/post hooks allow customization. If any
stage fails, the boot process halts with a clear error.

## Service Container

Services register with a lifecycle:

- **Singleton**: One instance for the process lifetime
- **Transient**: New instance on every resolution
- **Scoped**: One instance per scope context

```
container = ServiceContainer()
container.register("logger", lambda c: setup_logging())
container.register("gateway", lambda c: Gateway(c.resolve("config")))
container.start_all()
```

## Health Check System

Components register check functions:

```python
hc = HealthChecker()
hc.register("gateway.http", lambda: check_http())
hc.register("provider.openai", lambda: check_openai())
summary = hc.run_all()
```

Health states: healthy, degraded, unhealthy, unknown.

## Error Handling

Structured error hierarchy:

```
AetherOSError
├── ConfigError
├── NetworkError
├── ProviderError
├── AuthError
├── RuntimeError
└── StartupError
```

All errors produce user-friendly messages with recovery suggestions.
No raw tracebacks are shown to users.

## State Management

Global state tracks:

- Application lifecycle (initializing → starting → running → stopping)
- Component states (uninitialized → initializing → ready → busy → error)
- Key-value store with change listeners
- Optional persistent storage

## Security

- Fernet (AES-128-CBC) encryption for secrets
- PBKDF2 key derivation with 600,000 iterations
- Encrypted secret storage on disk (chmod 600)
- Auto-detection of secret keys by naming convention
- API key hashing for display

## Performance

- Lazy loading: values computed on first access, cached thereafter
- Lazy imports: modules imported on first attribute access
- Background loading: resource initialization in parallel threads
- Duplicate initialization guard
- Startup timing instrumentation

## Directory Structure

```
aetheros/
├── aetheros_arch/          # Architecture foundation (NEW)
│   ├── __init__.py
│   ├── config_manager.py
│   ├── health_checker.py
│   ├── error_handler.py
│   ├── service_container.py
│   ├── state_manager.py
│   ├── boot_sequence.py
│   ├── security_foundation.py
│   └── performance.py
├── config/                 # Configuration files (NEW)
│   ├── config.json
│   ├── settings.json
│   ├── providers.json
│   ├── gateway.json
│   ├── runtime.json
│   ├── memory.json
│   └── security.json
├── run_agent.py            # AIAgent class — core conversation loop
├── model_tools.py          # Tool orchestration
├── cli.py                  # Interactive CLI orchestrator
├── aetheros_state.py       # SessionDB — SQLite session store
├── aetheros_constants.py   # Profile-aware paths
├── aetheros_logging.py     # Centralized logging
├── agent/                  # Agent internals
├── aetheros_cli/           # CLI subcommands
├── tools/                  # Tool implementations
├── gateway/                # Messaging gateway
├── plugins/                # Plugin system
├── memory/                 # Memory system
├── providers/              # Provider base
├── skills/                 # Built-in skills
├── ui-tui/                 # Ink terminal UI
├── tui_gateway/            # TUI backend
├── apps/                   # Desktop & web apps
├── web/                    # Dashboard SPA
├── tests/                  # Test suite
└── docs/                   # Documentation
```