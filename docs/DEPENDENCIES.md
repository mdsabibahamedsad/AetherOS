# AetherOS Dependencies

**Generated:** July 14, 2026

---

## Python Dependencies (Core)

### Production (pinned exact)

| Package | Version | Purpose |
|---------|---------|---------|
| openai | 2.24.0 | LLM API client |
| python-dotenv | 1.2.2 | .env loading |
| fire | 0.7.1 | CLI argument parsing |
| httpx[socks] | 0.28.1 | HTTP client |
| rich | 14.3.3 | CLI formatting |
| tenacity | 9.1.4 | Retry logic |
| pyyaml | 6.0.3 | YAML parsing |
| ruamel.yaml | 0.18.17 | YAML round-trip |
| requests | 2.33.0 | Legacy HTTP |
| jinja2 | 3.1.6 | Template rendering |
| pydantic | 2.13.4 | Data validation |
| prompt_toolkit | 3.0.52 | Interactive CLI |
| croniter | 6.0.0 | Cron expression parsing |
| packaging | 26.0 | Version comparison |
| Markdown | 3.10.2 | Markdown→HTML |
| PyJWT[crypto] | 2.13.0 | JWT auth |
| Pillow | 12.2.0 | Image processing |
| psutil | 7.2.2 | Process management |
| pathspec | 1.1.1 | .gitignore matching |
| fastapi | >=0.104.0,<1 | Web server |
| uvicorn[standard] | >=0.24.0,<1 | ASGI server |
| tzdata | 2025.3 (win32) | Windows timezone |
| ptyprocess | >=0.7.0,<1 (POSIX) | PTY management |
| pywinpty | >=2.0.0,<3 (win32) | Windows PTY |
| urllib3 | >=2.7.0,<3 | HTTP client |

### Optional Extras

| Extra | Packages | Trigger |
|-------|----------|---------|
| anthropic | anthropic==0.87.0 | provider=anthropic |
| exa | exa-py==2.10.2 | Web search provider |
| firecrawl | firecrawl-py==4.17.0 | Web search provider |
| parallel-web | parallel-web==0.6.0 | Web search provider |
| fal | fal-client==0.13.1 | Image gen |
| edge-tts | edge-tts==7.2.7 | TTS provider |
| modal | modal==1.3.4 | Sandbox backend |
| daytona | daytona==0.155.0 | Sandbox backend |
| hindsight | hindsight-client==0.6.1 | Memory provider |
| messaging | python-telegram-bot, discord.py, slack-bolt, slack-sdk, aiohttp, qrcode | Chat platforms |
| slack | slack-bolt, slack-sdk, aiohttp | Slack gateway |
| matrix | mautrix[encryption], aiosqlite, asyncpg | Matrix gateway |
| wecom | defusedxml | WeCom callback |
| voice | faster-whisper, sounddevice, numpy | Local STT |
| tts-premium | elevenlabs | Premium TTS |
| mcp | mcp==1.26.0, starlette==1.0.1 | MCP client |
| google | google-api-python-client, google-auth libraries | Google Workspace |
| youtube | youtube-transcript-api | YouTube skills |
| web | fastapi, uvicorn, starlette | Dashboard server |
| bedrock | boto3 | AWS Bedrock |
| azure-identity | azure-identity | Azure auth |
| mistral | mistralai | Mistral provider |
| honcho | honcho-ai | Memory provider |
| acp | agent-client-protocol | Editor integration |
| dingtalk | dingtalk-stream, alibabacloud-dingtalk | DingTalk |
| feishu | lark-oapi | Feishu/Lark |
| nemo-relay | nemo-relay | Nemo relay |
| homeassistant | aiohttp | Home Assistant |
| sms | aiohttp | SMS gateway |
| computer-use | mcp, starlette | Computer use |
| dev | debugpy, pytest, pytest-asyncio, pytest-timeout, mcp, starlette, ty, ruff, setuptools | Development |

---

## JavaScript/TypeScript Dependencies

### Root Workspace

| Package | Version | Purpose |
|---------|---------|---------|
| agent-browser | ^0.26.0 | Browser automation |

### Desktop App (`apps/desktop/`)

| Package | Version | Purpose |
|---------|---------|---------|
| react | ^19.2.5 | UI framework |
| nanostores | ^1.3.0 | State management |
| electron | 40.9.3 (dev) | Desktop shell |
| electron-builder | ^26.8.1 (dev) | Installer builder |
| @assistant-ui/react | ^0.12.28 | Chat components |
| @xterm/xterm | ^6.0.0 | Terminal emulator |
| tailwindcss | ^4.2.4 | CSS framework |
| vite | ^8.0.10 (dev) | Build tool |
| typescript | ^6.0.3 (dev) | Type system |
| node-pty | 1.1.0 | PTY support |

### TUI (`ui-tui/`)

| Package | Version | Purpose |
|---------|---------|---------|
| ink | ^6.8.0 | React for terminal |
| react | ^19.2.4 | UI framework |
| nanostores | ^1.2.0 | State management |
| undici | ^6.25.0 | HTTP client |
| typescript | ^6.0.3 (dev) | Type system |
| esbuild | ~0.27.0 (dev) | Build tool |

### Web Dashboard (`web/`)

| Package | Version | Purpose |
|---------|---------|---------|
| react | ^19.2.4 | UI framework |
| react-router-dom | ^7.17.0 | Routing |
| @xterm/xterm | ^6.0.0 | Terminal emulator |
| @nous-research/ui | 0.18.2 | Design system |
| tailwindcss | ^4.2.1 | CSS framework |
| vite | ^7.3.1 (dev) | Build tool |
| typescript | ^6.0.3 (dev) | Type system |

### Bootstrap Installer (`apps/bootstrap-installer/`)

| Package | Version | Purpose |
|---------|---------|---------|
| Tauri (Rust) | (Cargo.toml) | Native installer |

---

## Infrastructure Dependencies

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | >=3.11,<3.14 | Runtime |
| Node.js | >=20.0.0 | JS runtime |
| Docker | Latest | Containerization |
| s6-overlay | 3.2.3.0 | Process supervision |
| SQLite | Bundled | Session storage |
| uv | 0.11.6 | Package management |
| Nix | Flake | Package/build system |
| Playwright | (npm) | Browser automation |
| ripgrep | System | File search |

---

## Dependency Policy

- All Python deps upper-bounded for supply-chain security
- Exact pins for direct deps (`==X.Y.Z`)
- Range pins with ceiling for transitives (`>=X,<Y`)
- Git URLs pinned to commit SHA
- GitHub Actions pinned to commit SHA + version comment
- Policy reinforced after Mini Shai-Hulud worm (May 2026)
