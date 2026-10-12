# AI Provider Configuration

## Supported Providers

| Provider | Type | API Key | Auto-Detect | Models |
|----------|------|---------|-------------|--------|
| OpenAI | Cloud | Required | No | gpt-4o, gpt-4o-mini, o3, o4-mini |
| Anthropic | Cloud | Required | No | claude-sonnet-4, claude-3.5-haiku |
| Google Gemini | Cloud | Required | No | gemini-2.5-pro, gemini-2.5-flash |
| OpenRouter | Cloud | Required | No | 200+ models |
| Ollama | Local | No | Yes | Configurable |
| LM Studio | Local | No | Yes | Configurable |
| llama.cpp | Local | No | No | Configurable |
| OpenAI Compatible | Cloud/Local | Optional | No | Configurable |
| Azure OpenAI | Cloud | Required | No | Configurable |
| Custom | Any | Optional | No | Configurable |

## Model Roles

Each provider can assign models to roles:

- **Default Model** — Used for general conversation
- **Reasoning Model** — Complex problem-solving (e.g., o3, claude-sonnet-4)
- **Coding Model** — Code generation and analysis
- **Vision Model** — Image understanding
- **Fast Model** — Quick responses, simple queries
- **Cheap Model** — Cost-optimized for bulk work
- **Offline Model** — Local fallback when offline

## Security

- API keys are encrypted with AES-256-GCM
- Encryption key derived from machine-specific data
- Keys stored in `config/secrets.json`
- Never stored in plaintext
- Never exposed to frontend after storage

## Local AI Detection

The installer automatically detects:
- **Ollama**: Binary present on `PATH` (check with `which`/`where`)
- **LM Studio**: Application installed in default location

When detected, the provider is added with the default endpoint URL
and flagged as auto-detected.
