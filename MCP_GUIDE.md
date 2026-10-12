# AetherOS MCP Guide

## What is MCP?

The **Model Context Protocol (MCP)** is an open protocol that standardizes how AI applications provide context and tools to language models. Think of MCP as a USB-C port for AI — a standard way to connect AI models with external data sources, APIs, and services.

In AetherOS, MCP servers are third-class citizens in the tool ecosystem (above plugins but below core tools), offering structured tool surfaces without growing the permanent model-tool schema.

## AetherOS MCP Architecture

```
AetherOS Agent
      │
      ▼
  MCP Client (built-in)
      │
      ├── Local MCP Servers (stdio transport)
      │     ├── Filesystem
      │     ├── SQLite
      │     ├── Puppeteer
      │     └── ...
      │
      └── Remote MCP Servers (SSE transport)
            ├── GitHub
            ├── Slack
            ├── Figma
            └── ...
```

AetherOS connects to MCP servers through its built-in MCP client. Each server exposes tools that the agent can invoke. Servers can run locally (stdio subprocess) or remotely (Server-Sent Events over HTTP).

### Key Components

- **MCP Client** — Built into AetherOS, manages connections to MCP servers
- **MCP Catalog** — Curated list of known MCP servers in AetherOS
- **Tool Bridge** — MCP tools are exposed to the agent like native tools
- **Health Monitor** — Periodic connection checks for all configured servers

## Adding an MCP Server

### Using the AetherOS CLI

```bash
# List available MCP servers in the catalog
aetheros mcp list

# Add a server from the catalog
aetheros mcp add filesystem

# Add a custom server
aetheros mcp add custom --command "npx @modelcontextprotocol/server-filesystem /path"
```

### Configuration in config.yaml

```yaml
mcp:
  servers:
    filesystem:
      enabled: true
      transport: stdio
      command: npx
      args:
        - "@modelcontextprotocol/server-filesystem"
        - "/path/to/allowed/directory"

    github:
      enabled: true
      transport: sse
      url: https://api.github.com/mcp
      headers:
        Authorization: "Bearer ${GITHUB_TOKEN}"

    sqlite:
      enabled: false
      transport: stdio
      command: uvx
      args:
        - "mcp-server-sqlite"
        - "--db-path"
        - "~/.aetheros/data/mcp/mydb.db"
```

### Via the Desktop Dashboard

1. Open AetherOS Desktop
2. Navigate to **Extensions > MCP** (or **Marketplace > MCP**)
3. Click **Add Server**
4. Choose from catalog or configure custom
5. Set transport type (stdio or SSE)
6. Configure command/URL and arguments
7. Save and enable

### Per-Profile MCP Servers

MCP server configurations respect AetherOS profiles:

```bash
# Add MCP server for a specific profile
aetheros -p work mcp add slack
aetheros -p personal mcp add filesystem --args /home/personal/docs
```

## MCP Server Configuration Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `enabled` | boolean | No | Enable/disable server (default: true) |
| `transport` | string | Yes | `stdio` or `sse` |
| `command` | string | For stdio | Executable command |
| `args` | string[] | For stdio | Command arguments |
| `url` | string | For SSE | Server endpoint URL |
| `headers` | object | No | HTTP headers for SSE transport |
| `timeout` | integer | No | Connection timeout in seconds (default: 30) |
| `env` | object | No | Environment variables for stdio transport |
| `auto_restart` | boolean | No | Auto-restart on crash (default: true) |
| `health_check` | object | No | Health check configuration |

## MCP Server Management

### Enable/Disable

```bash
aetheros mcp enable filesystem
aetheros mcp disable github
```

### Health Checks

```bash
# Check all servers
aetheros mcp health

# Check specific server
aetheros mcp health filesystem

# Watch mode (continuous checks)
aetheros mcp health --watch
```

### View Status

```bash
# List all configured servers with status
aetheros mcp status

# View server details and available tools
aetheros mcp inspect filesystem
```

### Logs

```bash
# View MCP server logs
aetheros logs --mcp

# Filter by server
aetheros logs --mcp filesystem
```

## Creating Custom MCP Servers

MCP servers can be written in any language. The protocol uses JSON-RPC over stdio or SSE.

### Python Example

```python
import json
import sys


def handle_request(request: dict) -> dict:
    method = request.get("method")

    if method == "initialize":
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {
                    "listChanged": False,
                },
            },
            "serverInfo": {
                "name": "custom-mcp-server",
                "version": "1.0.0",
            },
        }

    elif method == "tools/list":
        return {
            "tools": [
                {
                    "name": "greet",
                    "description": "Greet a person by name",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Name to greet",
                            },
                        },
                        "required": ["name"],
                    },
                },
            ],
        }

    elif method == "tools/call":
        tool_name = request["params"]["name"]
        arguments = request["params"]["arguments"]

        if tool_name == "greet":
            name = arguments.get("name", "World")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Hello, {name}!",
                    },
                ],
            }

    return {"error": {"code": -32601, "message": "Method not found"}}


def main():
    for line in sys.stdin:
        request = json.loads(line.strip())
        response = handle_request(request)
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
```

### Node.js Example

```javascript
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';

const server = new Server(
  {
    name: 'custom-mcp-server',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  },
);

server.setToolHandler(
  {
    name: 'greet',
    description: 'Greet a person by name',
    inputSchema: {
      type: 'object',
      properties: {
        name: { type: 'string', description: 'Name to greet' },
      },
      required: ['name'],
    },
  },
  async (request) => {
    const { name } = request.arguments;
    return {
      content: [{ type: 'text', text: `Hello, ${name}!` }],
    };
  },
);

const transport = new StdioServerTransport();
await server.connect(transport);
```

### Registering in AetherOS

```yaml
mcp:
  servers:
    custom-greeter:
      enabled: true
      transport: stdio
      command: python
      args:
        - "/path/to/custom-mcp-server.py"
```

## Security Considerations

1. **Scope file system access** — Use dedicated directories, not root
2. **Validate all inputs** — MCP servers receive untrusted input from the model
3. **Use environment variables for secrets** — Never hardcode tokens in config
4. **Enable only trusted servers** — Review server code before adding to catalog
5. **Network isolation** — Limit network access for stdio-based servers
6. **Rate limiting** — Implement rate limiting for SSE-based servers
7. **Audit logging** — Enable audit logging for production MCP servers

## Troubleshooting

### Server won't start

```bash
# Check if the command is available
which npx  # or the command used

# Test the server directly
echo '{"jsonrpc":"2.0","id":1,"method":"initialize"}' | npx @modelcontextprotocol/server-filesystem /tmp

# Check AetherOS logs
aetheros logs --mcp filesystem --level DEBUG
```

### Connection timeouts

```yaml
# Increase timeout in config.yaml
mcp:
  servers:
    remote-api:
      timeout: 60
```

### Tools not appearing

```bash
# Verify server is running
aetheros mcp status

# List available tools
aetheros mcp inspect remote-api

# Restart the server
aetheros mcp restart remote-api
```

## Example Configurations

### 1. Filesystem Server

```yaml
mcp:
  servers:
    filesystem:
      enabled: true
      transport: stdio
      command: npx
      args:
        - "-y"
        - "@modelcontextprotocol/server-filesystem"
        - "/home/user/projects"
        - "/home/user/documents"
```

### 2. GitHub Server

```yaml
mcp:
  servers:
    github:
      enabled: true
      transport: sse
      url: https://api.github.com/mcp
      headers:
        Authorization: "Bearer ${GITHUB_TOKEN}"
        User-Agent: "aetheros-mcp/1.0"
```

### 3. SQLite Server

```yaml
mcp:
  servers:
    sqlite:
      enabled: true
      transport: stdio
      command: uvx
      args:
        - "mcp-server-sqlite"
        - "--db-path"
        - "~/.aetheros/data/mcp/analytics.db"
```

### 4. Puppeteer/Browser Server

```yaml
mcp:
  servers:
    puppeteer:
      enabled: true
      transport: stdio
      command: npx
      args:
        - "-y"
        - "@modelcontextprotocol/server-puppeteer"
```

### 5. Memory Server

```yaml
mcp:
  servers:
    memory:
      enabled: true
      transport: stdio
      command: npx
      args:
        - "-y"
        - "@modelcontextprotocol/server-memory"
```

### 6. Slack Server

```yaml
mcp:
  servers:
    slack:
      enabled: true
      transport: sse
      url: https://slack.com/api/mcp
      headers:
        Authorization: "Bearer ${SLACK_BOT_TOKEN}"
```

### 7. Figma Server

```yaml
mcp:
  servers:
    figma:
      enabled: true
      transport: sse
      url: https://figma.com/api/mcp
      headers:
        Authorization: "Bearer ${FIGMA_ACCESS_TOKEN}"
```

### 8. Brave Search Server

```yaml
mcp:
  servers:
    brave-search:
      enabled: true
      transport: stdio
      command: npx
      args:
        - "-y"
        - "@modelcontextprotocol/server-brave-search"
      env:
        BRAVE_API_KEY: "${BRAVE_API_KEY}"
```

### 9. EverArt (Image Generation) Server

```yaml
mcp:
  servers:
    everart:
      enabled: true
      transport: stdio
      command: npx
      args:
        - "-y"
        - "@modelcontextprotocol/server-everart"
      env:
        EVERART_API_KEY: "${EVERART_API_KEY}"
```

### 10. PostgreSQL Server

```yaml
mcp:
  servers:
    postgres:
      enabled: true
      transport: stdio
      command: npx
      args:
        - "-y"
        - "@modelcontextprotocol/server-postgres"
        - "postgresql://user:pass@localhost:5432/mydb"
```

### 11. Redis Server

```yaml
mcp:
  servers:
    redis:
      enabled: true
      transport: stdio
      command: npx
      args:
        - "-y"
        - "@modelcontextprotocol/server-redis"
        - "redis://localhost:6379"
```

### 12. Sentry Server

```yaml
mcp:
  servers:
    sentry:
      enabled: true
      transport: stdio
      command: npx
      args:
        - "-y"
        - "@modelcontextprotocol/server-sentry"
      env:
        SENTRY_TOKEN: "${SENTRY_TOKEN}"
```

### 13. Cloudflare Server

```yaml
mcp:
  servers:
    cloudflare:
      enabled: true
      transport: stdio
      command: npx
      args:
        - "-y"
        - "@modelcontextprotocol/server-cloudflare"
      env:
        CLOUDFLARE_API_TOKEN: "${CLOUDFLARE_API_TOKEN}"
```

### 14. Linear Server

```yaml
mcp:
  servers:
    linear:
      enabled: true
      transport: stdio
      command: npx
      args:
        - "-y"
        - "@modelcontextprotocol/server-linear"
      env:
        LINEAR_API_KEY: "${LINEAR_API_KEY}"
```

### 15. Playwright Server

```yaml
mcp:
  servers:
    playwright:
      enabled: true
      transport: stdio
      command: npx
      args:
        - "-y"
        - "@modelcontextprotocol/server-playwright"
```

### 16. Sequential Thinking Server

```yaml
mcp:
  servers:
    sequential-thinking:
      enabled: true
      transport: stdio
      command: npx
      args:
        - "-y"
        - "@modelcontextprotocol/server-sequential-thinking"
```

### 17. Docker Server

```yaml
mcp:
  servers:
    docker:
      enabled: true
      transport: stdio
      command: npx
      args:
        - "-y"
        - "@modelcontextprotocol/server-docker"
```

### 18. Kubernetes Server

```yaml
mcp:
  servers:
    kubernetes:
      enabled: true
      transport: stdio
      command: npx
      args:
        - "-y"
        - "@modelcontextprotocol/server-kubernetes"
      env:
        KUBECONFIG: "~/.kube/config"
```

### 19. Gmail Server

```yaml
mcp:
  servers:
    gmail:
      enabled: true
      transport: stdio
      command: npx
      args:
        - "-y"
        - "@modelcontextprotocol/server-gmail"
      env:
        GMAIL_OAUTH_PATH: "${GMAIL_OAUTH_PATH}"
```

### 20. Google Calendar Server

```yaml
mcp:
  servers:
    google-calendar:
      enabled: true
      transport: stdio
      command: npx
      args:
        - "-y"
        - "@modelcontextprotocol/server-google-calendar"
      env:
        GOOGLE_CALENDAR_OAUTH_PATH: "${GOOGLE_CALENDAR_OAUTH_PATH}"
```

### 21. Google Maps Server

```yaml
mcp:
  servers:
    google-maps:
      enabled: true
      transport: stdio
      command: npx
      args:
        - "-y"
        - "@modelcontextprotocol/server-google-maps"
      env:
        GOOGLE_MAPS_API_KEY: "${GOOGLE_MAPS_API_KEY}"
```

### 22. Shopify Server

```yaml
mcp:
  servers:
    shopify:
      enabled: true
      transport: stdio
      command: npx
      args:
        "-y"
        - "@modelcontextprotocol/server-shopify"
      env:
        SHOPIFY_STORE_URL: "${SHOPIFY_STORE_URL}"
        SHOPIFY_ACCESS_TOKEN: "${SHOPIFY_ACCESS_TOKEN}"
```

### 23. Stripe Server

```yaml
mcp:
  servers:
    stripe:
      enabled: true
      transport: stdio
      command: npx
      args:
        - "-y"
        - "@modelcontextprotocol/server-stripe"
      env:
        STRIPE_SECRET_KEY: "${STRIPE_SECRET_KEY}"
```
