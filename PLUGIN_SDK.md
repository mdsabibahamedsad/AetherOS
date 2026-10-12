# AetherOS Plugin SDK

## Introduction

AetherOS features a powerful plugin system that allows developers to extend the platform with custom capabilities. Plugins can register new tools, lifecycle hooks, CLI subcommands, and integrate deeply with the agent runtime — all without modifying core files.

## Architecture Overview

```
Plugin Discovery
  ├── ~/.aetheros/plugins/<name>/  (user-installed)
  ├── <repo>/plugins/<name>/        (bundled)
  └── pip entry_points              (package-installed)
        │
        ▼
  PluginManager (aetheros_cli/plugins.py)
        │
        ▼
  register(ctx)  ←── Plugin entry point
        │
        ├── ctx.register_tool(...)       → New tools
        ├── ctx.register_hook(...)       → Lifecycle hooks
        └── ctx.register_cli_command(...) → CLI subcommands
```

### Plugin Loader

The `PluginManager` discovers plugins at startup from multiple locations:
- `~/.aetheros/plugins/<name>/` — user-installed plugins
- `<repo>/plugins/<name>/` — bundled plugins shipped with AetherOS
- Pip entry points — plugins installed as Python packages

Each plugin directory must contain:
- `plugin.yaml` — plugin manifest
- `__init__.py` — plugin implementation with `register(ctx)` function

### Lifecycle Hooks

Plugins can hook into the agent lifecycle at these points:

| Hook | Trigger | Arguments |
|------|---------|-----------|
| `pre_tool_call` | Before any tool executes | `tool_name, args, ctx` |
| `post_tool_call` | After any tool completes | `tool_name, args, result, ctx` |
| `pre_llm_call` | Before LLM API call | `messages, model, ctx` |
| `post_llm_call` | After LLM API response | `messages, response, ctx` |
| `on_session_start` | New conversation session | `session_id, ctx` |
| `on_session_end` | Session ends | `session_id, ctx` |

### Plugin Manifest Format

Each plugin requires a `plugin.yaml` manifest:

```yaml
name: my-plugin
version: 1.0.0
description: Extends AetherOS with custom analytics
author: Your Name
license: MIT

entry: __init__.py
register: register

kind: plugin

hooks:
  - pre_tool_call
  - post_llm_call

tools:
  - my_analytics_tool

cli_commands: true

permissions:
  - network
  - filesystem:read
  - filesystem:write

config:
  api_endpoint:
    type: string
    default: https://api.example.com
    description: API endpoint URL
  refresh_interval:
    type: integer
    default: 60
    description: Polling interval in seconds
```

### Creating a Plugin

#### Step 1: Create the directory structure

```
~/.aetheros/plugins/my-analytics/
├── plugin.yaml
└── __init__.py
```

#### Step 2: Write the manifest (`plugin.yaml`)

```yaml
name: my-analytics
version: 0.1.0
description: Custom analytics tools for AetherOS
author: Your Name
license: MIT
entry: __init__.py
register: register
permissions:
  - network
```

#### Step 3: Implement the plugin (`__init__.py`)

```python
from aetheros.plugin import PluginContext


def register(ctx: PluginContext) -> None:
    """Register plugin capabilities with the AetherOS runtime."""

    # Register a tool
    ctx.register_tool(
        name="my_analytics_query",
        description="Query custom analytics data",
        parameters={
            "type": "object",
            "properties": {
                "metric": {
                    "type": "string",
                    "description": "Metric to query",
                    "enum": ["users", "events", "revenue"],
                },
                "period": {
                    "type": "string",
                    "description": "Time period",
                    "enum": ["24h", "7d", "30d"],
                },
            },
            "required": ["metric"],
        },
        handler=handle_analytics_query,
    )

    # Register a lifecycle hook
    ctx.register_hook("post_llm_call", on_post_llm_call)


def handle_analytics_query(metric: str, period: str = "24h", **kwargs) -> str:
    """Handle the analytics query tool call."""
    import json
    # Your analytics logic here
    return json.dumps({
        "metric": metric,
        "period": period,
        "value": 42,
        "unit": "count",
    })


def on_post_llm_call(messages: list, response: dict, **kwargs) -> None:
    """Post-LLM hook to log analytics."""
    import logging
    logger = logging.getLogger(__name__)
    logger.debug("LLM call completed: %s tokens", response.get("usage", {}).get("total_tokens"))
```

#### Step 4: Enable the plugin

```bash
aetheros plugins enable my-analytics
```

### Plugin API Reference

#### PluginContext Methods

| Method | Description |
|--------|-------------|
| `register_tool(name, description, parameters, handler)` | Register a new agent tool |
| `register_hook(event, handler)` | Register a lifecycle hook handler |
| `register_cli_command(name, parser, handler)` | Register a new CLI subcommand |
| `get_config()` | Read plugin configuration |
| `get_aetheros_home()` | Get the active AetherOS home directory |
| `log(level, message)` | Log through the AetherOS logging system |

#### Available Hooks

| Hook | Signature |
|------|-----------|
| `pre_tool_call` | `handler(tool_name: str, args: dict, ctx: dict) -> None` |
| `post_tool_call` | `handler(tool_name: str, args: dict, result: str, ctx: dict) -> None` |
| `pre_llm_call` | `handler(messages: list, model: str, ctx: dict) -> None` |
| `post_llm_call` | `handler(messages: list, response: dict, ctx: dict) -> None` |
| `on_session_start` | `handler(session_id: str, ctx: dict) -> None` |
| `on_session_end` | `handler(session_id: str, ctx: dict) -> None` |

#### Utility Functions

| Function | Description |
|----------|-------------|
| `get_aetheros_home()` | Returns the active profile's home directory |
| `get_plugin_data_dir()` | Returns the plugin's data directory (`~/.aetheros/plugins/<name>/data/`) |
| `make_http_request(method, url, **kwargs)` | Makes authenticated HTTP requests through AetherOS proxy |

### Permission System

Plugins require explicit permission declarations in their manifest. The permission system has three categories:

| Category | Modes | Description |
|----------|-------|-------------|
| `network` | `allow` / `deny` | HTTP/network access |
| `filesystem:read` | `allow` / `deny` | Read files outside plugin dir |
| `filesystem:write` | `allow` / `deny` | Write files outside plugin dir |
| `process` | `allow` / `deny` | Spawn subprocesses |
| `environment` | `allow` / `deny` | Read environment variables |
| `secrets` | `allow` / `deny` | Access credential store |

Best practices:
- Request the minimum permissions your plugin needs
- Use `filesystem:read` scoped to specific paths when possible
- Avoid `network` if your plugin is purely local
- Document what each permission is used for in your manifest

### Distribution and Marketplace Submission

1. Package your plugin as a Python package or standalone directory
2. Create a `plugin.yaml` manifest with all required metadata
3. Test locally: `aetheros plugins install <path>`
4. Submit to the marketplace: `aetheros plugins publish`
5. Marketplace listing includes: name, description, version, author, permissions, screenshots

### Testing Plugins

```bash
# Install from local path
aetheros plugins install ./my-plugin

# Enable/disable
aetheros plugins enable my-plugin
aetheros plugins disable my-plugin

# List installed plugins
aetheros plugins list

# View plugin logs
aetheros logs --plugin my-plugin

# Test in isolation
aetheros --plugin my-plugin "run my custom command"
```

### Best Practices

1. **Keep plugins focused** — each plugin should do one thing well
2. **Minimize tool surface** — register only the tools you need
3. **Handle errors gracefully** — always return meaningful error messages
4. **Use async where possible** — non-blocking hooks prevent agent delays
5. **Respect prompt caching** — don't mutate shared state mid-conversation
6. **Version your plugin** — use semantic versioning in manifest
7. **Log thoughtfully** — verbose logs help debugging, but don't spam agent.log
8. **Test across platforms** — ensure your plugin works on Linux, macOS, and Windows

### Example: Complete Plugin Walkthrough

**Weather Plugin** — Adds a `/weather` command and weather lookup tool.

`plugin.yaml`:
```yaml
name: weather
version: 1.0.0
description: Weather lookup tool and command
author: AetherOS
license: MIT
entry: __init__.py
register: register
permissions:
  - network
```

`__init__.py`:
```python
import json
from aetheros.plugin import PluginContext


def register(ctx: PluginContext) -> None:
    ctx.register_tool(
        name="get_weather",
        description="Get current weather for a location",
        parameters={
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name or coordinates",
                },
            },
            "required": ["location"],
        },
        handler=get_weather_handler,
    )

    ctx.register_cli_command(
        name="weather",
        help="Get weather information",
        handler=cli_weather_handler,
    )


def get_weather_handler(location: str, **kwargs) -> str:
    import urllib.request
    url = f"https://api.weather.example/v1/current?q={location}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
        return json.dumps({
            "location": data["name"],
            "temperature": data["main"]["temp"],
            "conditions": data["weather"][0]["description"],
            "humidity": data["main"]["humidity"],
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


def cli_weather_handler(args: list) -> None:
    import sys
    if not args:
        print("Usage: aetheros weather <location>")
        return
    result = json.loads(get_weather_handler(location=" ".join(args)))
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Weather for {result['location']}:")
        print(f"  Temperature: {result['temperature']}°C")
        print(f"  Conditions: {result['conditions']}")
        print(f"  Humidity: {result['humidity']}%")
```
